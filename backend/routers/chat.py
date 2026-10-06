import os
import json

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


load_dotenv()


router = APIRouter(
    prefix="/chat",
    tags=["AI Chatbot"]
)


# ---------------------------------------------------------
# OpenRouter Client
# ---------------------------------------------------------

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)


# ---------------------------------------------------------
# Separate MCP Servers
# ---------------------------------------------------------

HOTEL_MCP_SERVER_URL = os.getenv(
    "HOTEL_MCP_SERVER_URL",
    "http://127.0.0.1:8002/mcp"
)

TRANSPORT_MCP_SERVER_URL = os.getenv(
    "TRANSPORT_MCP_SERVER_URL",
    "http://127.0.0.1:8003/mcp"
)


# ---------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class HotelData(BaseModel):
    id: int
    name: str
    address: str | None = None
    district: str | None = None
    accommodation_type: str | None = None
    registration_no: str | None = None
    licence_no: str | None = None
    source: str | None = None
    price_per_night: float | None = None
    rating: float | None = None
    available: bool | None = None
    city_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    hotels: list[HotelData] = Field(default_factory=list)
    selected_hotel: HotelData | None = None


# ---------------------------------------------------------
# MCP Helpers
# ---------------------------------------------------------

async def get_openai_tools(session: ClientSession):
    """
    Convert MCP tools to OpenAI/OpenRouter
    Chat Completions tool format.
    """

    result = await session.list_tools()

    tools = []

    for tool in result.tools:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
        )

    return tools


def get_mcp_result_text(mcp_result) -> str:
    """
    Convert MCP tool result into plain text
    that can be sent back to the LLM.
    """

    result_text = ""

    for content in mcp_result.content:
        if hasattr(content, "text"):
            result_text += content.text

    return result_text


def build_conversation_input(request: ChatRequest):
    """
    Build Chat Completions message history.
    """

    conversation = []

    # Keep the most recent 20 messages
    recent_history = request.history[-20:]

    for message in recent_history:
        if message.role not in ["user", "assistant"]:
            continue

        conversation.append(
            {
                "role": message.role,
                "content": message.content
            }
        )

    # Avoid adding the current message twice
    if (
        not conversation
        or conversation[-1]["role"] != "user"
        or conversation[-1]["content"] != request.message
    ):
        conversation.append(
            {
                "role": "user",
                "content": request.message
            }
        )

    return conversation


# ---------------------------------------------------------
# System Instructions
# ---------------------------------------------------------

SYSTEM_INSTRUCTIONS = """
You are the AI assistant for the SerendibStay Sri Lanka hotel and
transport system.

You can help users with:
- searching hotels
- getting hotel details
- creating hotel bookings
- searching transport providers
- getting transport provider details
- creating transport requests

Use the available MCP tools whenever real system data or an action is
required.

Hotel tools belong to the Hotel MCP server.
Transport tools belong to the Transport MCP server.

Recognize common spelling mistakes and alternative spellings of Sri
Lankan districts and cities before calling tools.

For example, treat "Rathnapura" as "Ratnapura" when the intended
location is clear.

Do not invent a district, city, hotel, transport provider, price,
rating, availability, registration number, licence number, booking,
or transport request.

Use information already supplied in the conversation. Do not ask the
user again for information that they have already provided.

For transport:
- Search using the service district and passenger count.
- A transport request is not confirmed just because it was created.
- If the tool returns status "pending", clearly tell the user that the
  request is pending provider acceptance.
- Do not claim that a provider accepted a request unless the system
  explicitly says so.

For hotel bookings:
- Do not claim that a booking was created unless the booking tool
  successfully returns confirmation.

When creating a transport request, use the selected provider ID and all
customer/trip details already supplied by the user.

Never show raw JSON, Python dictionaries, arrays, database records,
API responses, MCP tool output, internal IDs, or raw tool results to
the user.

After receiving tool data, convert it into a clean, human-friendly
answer.

For hotel search results:
- Present each hotel clearly with its name and useful customer-facing
  details.
- Do not dump the raw hotel tool response.

For transport search results:
- Present providers as a clean Markdown list.
- Include useful details such as provider/driver name, vehicle,
  capacity, rating, price, and service area when available.
- Do not display the raw transport tool response before or after the
  formatted answer.

Do not repeat the same search results in multiple formats.

Only include internal database IDs when they are genuinely useful for
the next user action. Otherwise, keep internal IDs hidden.

Use Markdown for presentation, but keep the response concise and easy
to scan.


Keep answers clear, concise, and helpful.
"""


# ---------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:

        # -------------------------------------------------
        # Connect to Hotel MCP
        # -------------------------------------------------

        async with streamable_http_client(
            HOTEL_MCP_SERVER_URL
        ) as (hotel_read, hotel_write):

            async with ClientSession(
                hotel_read,
                hotel_write
            ) as hotel_session:

                await hotel_session.initialize()

                hotel_tools = await get_openai_tools(
                    hotel_session
                )

                hotel_tool_names = {
                    tool["function"]["name"]
                    for tool in hotel_tools
                }

                # -----------------------------------------
                # Connect to Transport MCP
                # -----------------------------------------

                async with streamable_http_client(
                    TRANSPORT_MCP_SERVER_URL
                ) as (transport_read, transport_write):

                    async with ClientSession(
                        transport_read,
                        transport_write
                    ) as transport_session:

                        await transport_session.initialize()

                        transport_tools = await get_openai_tools(
                            transport_session
                        )

                        transport_tool_names = {
                            tool["function"]["name"]
                            for tool in transport_tools
                        }

                        # ---------------------------------
                        # Combine Hotel + Transport tools
                        # ---------------------------------

                        tools = (
                            hotel_tools
                            + transport_tools
                        )

                        conversation_input = (
                            build_conversation_input(
                                request
                            )
                        )

                        # Chat Completions messages
                        messages = [
                            {
                                "role": "system",
                                "content": SYSTEM_INSTRUCTIONS
                            }
                        ]

                        messages.extend(conversation_input)

                        # ---------------------------------
                        # Multi-step AI + MCP tool loop
                        # ---------------------------------

                        for _ in range(6):

                            response = client.chat.completions.create(
                                model=OPENROUTER_MODEL,
                                messages=messages,
                                tools=tools,
                                tool_choice="auto"
                            )

                            if not response.choices:
                                return ChatResponse(
                                    reply=(
                                        "I could not generate "
                                        "a response."
                                    )
                                )

                            assistant_message = (
                                response.choices[0].message
                            )

                            tool_calls = (
                                assistant_message.tool_calls or []
                            )

                            # ---------------------------------
                            # No tool call -> final AI answer
                            # ---------------------------------

                            if not tool_calls:

                                reply = (
                                    assistant_message.content
                                    or
                                    "I could not generate a response."
                                )

                                return ChatResponse(
                                    reply=reply
                                )

                            # ---------------------------------
                            # Add assistant tool-call message
                            # to conversation
                            # ---------------------------------

                            assistant_tool_calls = []

                            for tool_call in tool_calls:

                                assistant_tool_calls.append(
                                    {
                                        "id": tool_call.id,
                                        "type": "function",
                                        "function": {
                                            "name":
                                                tool_call.function.name,
                                            "arguments":
                                                tool_call.function.arguments,
                                        },
                                    }
                                )

                            messages.append(
                                {
                                    "role": "assistant",
                                    "content":
                                        assistant_message.content,
                                    "tool_calls":
                                        assistant_tool_calls,
                                }
                            )

                            # ---------------------------------
                            # Execute requested MCP tools
                            # ---------------------------------

                            for tool_call in tool_calls:

                                tool_name = (
                                    tool_call.function.name
                                )

                                try:
                                    arguments = json.loads(
                                        tool_call.function.arguments
                                        or "{}"
                                    )

                                except json.JSONDecodeError:
                                    arguments = {}

                                # -----------------------------
                                # Hotel MCP tool
                                # -----------------------------

                                if tool_name in hotel_tool_names:

                                    mcp_result = (
                                        await hotel_session.call_tool(
                                            tool_name,
                                            arguments
                                        )
                                    )

                                    result_text = (
                                        get_mcp_result_text(
                                            mcp_result
                                        )
                                    )

                                # -----------------------------
                                # Transport MCP tool
                                # -----------------------------

                                elif tool_name in transport_tool_names:

                                    mcp_result = (
                                        await transport_session.call_tool(
                                            tool_name,
                                            arguments
                                        )
                                    )

                                    result_text = (
                                        get_mcp_result_text(
                                            mcp_result
                                        )
                                    )

                                # -----------------------------
                                # Unknown tool
                                # -----------------------------

                                else:

                                    result_text = json.dumps(
                                        {
                                            "error":
                                                f"Unknown tool: "
                                                f"{tool_name}"
                                        }
                                    )

                                # Tool returned no text
                                if not result_text:

                                    result_text = json.dumps(
                                        {
                                            "error":
                                                "Tool returned no data"
                                        }
                                    )

                                # -----------------------------
                                # Return MCP result to AI
                                # -----------------------------

                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id":
                                            tool_call.id,
                                        "content":
                                            result_text,
                                    }
                                )

                        # ---------------------------------
                        # Too many tool calls
                        # ---------------------------------

                        return ChatResponse(
                            reply=(
                                "I could not complete the request "
                                "after several system operations."
                            )
                        )

    except Exception as e:

        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"AI/MCP service error: {str(e)}"
        )