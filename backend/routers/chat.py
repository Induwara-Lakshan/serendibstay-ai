import os
import json

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


load_dotenv()

router = APIRouter(
    prefix="/chat",
    tags=["AI Chatbot"]
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MCP_SERVER_URL = "http://127.0.0.1:8002/mcp"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# Convert MCP tools into OpenAI function tools
async def get_openai_tools(session: ClientSession):
    result = await session.list_tools()

    tools = []

    for tool in result.tools:
        tools.append(
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description or "",
               "parameters": tool.input_schema,
            }
        )

    return tools


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:
        # Connect to MCP Server
        async with streamable_http_client(
            MCP_SERVER_URL
        ) as (read, write):

            async with ClientSession(read, write) as session:

                # Initialize MCP connection
                await session.initialize()

                # Get the 5 MCP tools
                tools = await get_openai_tools(session)

                # Ask OpenAI
                response = client.responses.create(
                    model="gpt-5.6-luna",
                    instructions=(
                        "Recognize common spelling mistakes and alternative spellings of Sri Lankan "
"districts and cities before calling a tool. "
"For example, treat 'Rathnapura' as 'Ratnapura'. "
"When a user misspells a district or city but the intended location is clear, "
"use the correct official location name when calling the hotel tool. "
"Do not invent a location when the intended place is unclear. "
                    ),
                    input=request.message,
                    tools=tools
                )

                # Check whether OpenAI requested MCP tools
                tool_outputs = []

                for item in response.output:

                    if item.type == "function_call":

                        tool_name = item.name

                        arguments = json.loads(
                            item.arguments
                        )

                        # Call the actual MCP tool
                        mcp_result = await session.call_tool(
                            tool_name,
                            arguments
                        )

                        # Convert MCP result to text
                        result_text = ""

                        for content in mcp_result.content:
                            if hasattr(content, "text"):
                                result_text += content.text

                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": result_text
                            }
                        )

                # If a tool was used, send its result back to OpenAI
                if tool_outputs:

                    final_response = client.responses.create(
                        model="gpt-5.6-luna",
                        instructions=(
                            "You are an AI assistant for the Sri Lanka Hotel system. "
                            "Answer using the hotel data returned by the tools. "
                            "Do not invent missing information. "
                            "Keep answers clear and concise."
                        ),
                        previous_response_id=response.id,
                        input=tool_outputs,
                        tools=tools
                    )

                    return ChatResponse(
                        reply=final_response.output_text
                    )

                # Normal question where no MCP tool is required
                return ChatResponse(
                    reply=response.output_text
                )

    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"AI/MCP service error: {str(e)}"
    ) 