from database import SessionLocal
from models import City, Hotel


# -------------------------------------------------------------------
# Sri Lanka accommodation seed data
# -------------------------------------------------------------------
# Policy used for this academic project:
# - Minimum 5 real accommodation establishments per district (25 districts).
# - No invented ratings or prices: those fields are stored as None.
# - Registration/licence numbers are included only where directly verified
#   from 2026 Sri Lanka Tourism / SLTDA-indexed records available during
#   dataset preparation. Otherwise they are left as None instead of guessed.
# - "available=True" means the establishment is included/active in this
#   project dataset; it is NOT a real-time room-availability claim.
#
# Total records: 125 (5 x 25 districts)
# -------------------------------------------------------------------

PROVINCES = {
    "Colombo": "Western",
    "Gampaha": "Western",
    "Kalutara": "Western",
    "Kandy": "Central",
    "Matale": "Central",
    "Nuwara Eliya": "Central",
    "Galle": "Southern",
    "Matara": "Southern",
    "Hambantota": "Southern",
    "Jaffna": "Northern",
    "Kilinochchi": "Northern",
    "Mannar": "Northern",
    "Mullaitivu": "Northern",
    "Vavuniya": "Northern",
    "Batticaloa": "Eastern",
    "Ampara": "Eastern",
    "Trincomalee": "Eastern",
    "Kurunegala": "North Western",
    "Puttalam": "North Western",
    "Anuradhapura": "North Central",
    "Polonnaruwa": "North Central",
    "Badulla": "Uva",
    "Monaragala": "Uva",
    "Ratnapura": "Sabaragamuwa",
    "Kegalle": "Sabaragamuwa",
}

# Each item:
# name, city, district, accommodation_type, address,
# registration_no, licence_no, source
HOTELS = [
    # ---------------- Colombo ----------------
    dict(name="ITC Ratnadipa", city="Colombo", district="Colombo", accommodation_type="Hotel",
         address="Galle Face Center Road, Colombo 01",
         registration_no="SLTDA/SQA/HC/00237", licence_no="HC/2025/017", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="NH Collection Colombo", city="Colombo", district="Colombo", accommodation_type="Hotel",
         address="Sir M. Anagarika Dharmapala Mawatha, Colombo 03",
         registration_no="SLTDA/SQA/HC/00202", licence_no="HC/2026/0118", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Nuwa", city="Colombo", district="Colombo", accommodation_type="Hotel",
         address="Justice Akbar Mawatha, Colombo 02",
         registration_no="SLTDA/SQA/HC/00238", licence_no="HC/2026/0089", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Jetwing Colombo Seven", city="Colombo", district="Colombo", accommodation_type="Hotel",
         address="Ward Place, Colombo 07",
         registration_no="SLTDA/SQA/HC/00230", licence_no="HC/2026/010", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Fairview Hotel", city="Colombo", district="Colombo", accommodation_type="Hotel",
         address="Ramakrishna Road, Colombo 06",
         registration_no="SLTDA/SQA/HC/00170", licence_no="HC/2026/0071", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),

    # ---------------- Gampaha ----------------
    dict(name="Goldi Sands Hotel", city="Negombo", district="Gampaha", accommodation_type="Hotel",
         address="Ethukala, Negombo",
         registration_no="SLTDA/SQA/HC/086", licence_no="HC/2026/025", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Jetwing Ayurveda", city="Negombo", district="Gampaha", accommodation_type="Hotel",
         address="Ethukala, Negombo",
         registration_no="SLTDA/SQA/TH/161", licence_no="TH/2026/0014", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Jetwing Blue", city="Negombo", district="Gampaha", accommodation_type="Hotel",
         address="Negombo, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Heritance Negombo", city="Negombo", district="Gampaha", accommodation_type="Hotel",
         address="Negombo, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Camelot Beach Hotel", city="Negombo", district="Gampaha", accommodation_type="Hotel",
         address="Negombo, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Kalutara ----------------
    dict(name="Anantara Kalutara Resort", city="Kalutara", district="Kalutara", accommodation_type="Resort",
         address="Kalutara, Sri Lanka", registration_no="SLTDA/SQA/HC/00205", licence_no="HC/2026/054", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Tangerine Beach Hotel", city="Kalutara", district="Kalutara", accommodation_type="Hotel",
         address="Kalutara, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Royal Palms Beach Hotel", city="Kalutara", district="Kalutara", accommodation_type="Hotel",
         address="Kalutara, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Avani Kalutara Resort", city="Kalutara", district="Kalutara", accommodation_type="Resort",
         address="Kalutara, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Club Waskaduwa Beach Resort & Spa", city="Waskaduwa", district="Kalutara", accommodation_type="Resort",
         address="Waskaduwa, Kalutara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Kandy ----------------
    dict(name="Earl's Regency Hotel", city="Kandy", district="Kandy", accommodation_type="Hotel",
         address="Tennekumbura, Kandy", registration_no="SLTDA/SQA/HC/089", licence_no="HC/2026/0122", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Earls Regent Hotel", city="Kandy", district="Kandy", accommodation_type="Hotel",
         address="Devenirajasinha Road, Peradeniya, Kandy", registration_no="SLTDA/SQA/HC/00169", licence_no="HC/2026/0087", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Jetwing Kandy Gallery", city="Kandy", district="Kandy", accommodation_type="Hotel",
         address="Haragama, Kandy", registration_no="SLTDA/SQA/TH/00408", licence_no="TH/2026/0008", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Hotel Suisse", city="Kandy", district="Kandy", accommodation_type="Hotel",
         address="Sangaraja Mawatha, Kandy", registration_no="SLTDA/SQA/TH/094", licence_no="TH/2026/0036", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Fox Kandy", city="Kandy", district="Kandy", accommodation_type="Hotel",
         address="Richmond Hill, Heerassagala, Kandy", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Matale ----------------
    dict(name="Heritance Kandalama", city="Dambulla", district="Matale", accommodation_type="Hotel",
         address="Kandalama, Dambulla", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Jetwing Lake", city="Dambulla", district="Matale", accommodation_type="Hotel",
         address="Dambulla, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Nivadoo Resort Sigiriya", city="Sigiriya", district="Matale", accommodation_type="Hotel",
         address="Pothana, Kimbissa, Sigiriya", registration_no="SLTDA/SQA/TH/00441", licence_no="TH/2026/0011", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Aliya Resort & Spa", city="Sigiriya", district="Matale", accommodation_type="Resort",
         address="Sigiriya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Sigiriya Village Hotel", city="Sigiriya", district="Matale", accommodation_type="Hotel",
         address="Sigiriya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Nuwara Eliya ----------------
    dict(name="The Grand Hotel", city="Nuwara Eliya", district="Nuwara Eliya", accommodation_type="Hotel",
         address="Nuwara Eliya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Araliya Green City", city="Nuwara Eliya", district="Nuwara Eliya", accommodation_type="Hotel",
         address="Nuwara Eliya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Heritance Tea Factory", city="Kandapola", district="Nuwara Eliya", accommodation_type="Hotel",
         address="Kandapola, Nuwara Eliya", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Jetwing St. Andrew's", city="Nuwara Eliya", district="Nuwara Eliya", accommodation_type="Hotel",
         address="Nuwara Eliya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Galway Heights Hotel", city="Nuwara Eliya", district="Nuwara Eliya", accommodation_type="Hotel",
         address="Nuwara Eliya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Galle ----------------
    dict(name="Jetwing Lighthouse", city="Galle", district="Galle", accommodation_type="Hotel",
         address="Galle, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Radisson Blu Resort Galle", city="Galle", district="Galle", accommodation_type="Resort",
         address="Galle, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Le Grand Galle", city="Galle", district="Galle", accommodation_type="Hotel",
         address="Galle, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Fort Bazaar", city="Galle", district="Galle", accommodation_type="Boutique Hotel",
         address="Galle Fort, Galle", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Insight Resort", city="Ahangama", district="Galle", accommodation_type="Hotel",
         address="Matara Road, Ahangama", registration_no="SLTDA/SQA/TH/129", licence_no="TH/2026/0009", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),

    # ---------------- Matara ----------------
    dict(name="Weligama Bay Marriott Resort & Spa", city="Weligama", district="Matara", accommodation_type="Resort",
         address="Weligama, Matara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Cape Weligama", city="Weligama", district="Matara", accommodation_type="Resort",
         address="Weligama, Matara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Mandara Resort Mirissa", city="Mirissa", district="Matara", accommodation_type="Resort",
         address="Mirissa, Matara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Lantern Boutique Hotel", city="Mirissa", district="Matara", accommodation_type="Boutique Hotel",
         address="Mirissa, Matara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Triple O Six", city="Mirissa", district="Matara", accommodation_type="Hotel",
         address="Mirissa, Matara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Hambantota ----------------
    dict(name="Shangri-La Hambantota", city="Hambantota", district="Hambantota", accommodation_type="Resort",
         address="Hambantota, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="DoubleTree by Hilton Weerawila Rajawarna Resort", city="Weerawila", district="Hambantota", accommodation_type="Resort",
         address="Weerawila Wattha, Weerawila", registration_no="SLTDA/SQA/HC/00210", licence_no="HC/2026/0124", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Anantara Peace Haven Tangalle Resort", city="Tangalle", district="Hambantota", accommodation_type="Resort",
         address="Goyambokka Estate, Tangalle", registration_no="SLTDA/SQA/HC/00172", licence_no="HC/2026/053", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Sooriya Resort & Spa", city="Tangalle", district="Hambantota", accommodation_type="Resort",
         address="Tangalle, Hambantota", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Golden Pearl Beach Resort", city="Tangalle", district="Hambantota", accommodation_type="Hotel",
         address="Madaketiya Road, Tangalle", registration_no="SLTDA/SQA/TH/00453", licence_no="TH/2026/0081", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),

    # ---------------- Jaffna ----------------
    dict(name="Jaffna Heritage Hotel", city="Jaffna", district="Jaffna", accommodation_type="Hotel",
         address="Temple Road, Nallur, Jaffna", registration_no="SLTDA/SQA/TH/00262", licence_no="TH/2026/0108", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Jetwing Jaffna", city="Jaffna", district="Jaffna", accommodation_type="Hotel",
         address="Mahatma Gandhi Road, Jaffna", registration_no="SLTDA/SQA/HC/00203", licence_no="HC/2026/004", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Fox Jaffna by Fox Resorts", city="Jaffna", district="Jaffna", accommodation_type="Hotel",
         address="K.K.S. Road, Jaffna", registration_no="SLTDA/SQA/TH/00402", licence_no="TH/2026/0096", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="North Gate Jaffna", city="Jaffna", district="Jaffna", accommodation_type="Hotel",
         address="Martyn Road, Jaffna", registration_no="SLTDA/SQA/HC/00204", licence_no="HC/2026/0105", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Tilko Jaffna City Hotel", city="Jaffna", district="Jaffna", accommodation_type="Guest House",
         address="K.K.S. Road, Jaffna", registration_no="SLTDA/SQA/GH/0920", licence_no="GH/2026/0744", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),

    # ---------------- Kilinochchi ----------------
    dict(name="Hotel Sella Rest", city="Kilinochchi", district="Kilinochchi", accommodation_type="Guest House",
         address="Uthayangar West, Kilinochchi", registration_no="SLTDA/SQA/GH/1098", licence_no="GH/2026/0600", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="ReeCha Organic Resort", city="Kilinochchi", district="Kilinochchi", accommodation_type="Resort",
         address="Kilinochchi District, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="AKR Hotel", city="Kilinochchi", district="Kilinochchi", accommodation_type="Hotel",
         address="Kilinochchi, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Friends Paradise", city="Kilinochchi", district="Kilinochchi", accommodation_type="Guest House",
         address="Kilinochchi, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="RJ Mahaal Hotel", city="Kilinochchi", district="Kilinochchi", accommodation_type="Hotel",
         address="Kilinochchi, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Mannar ----------------
    dict(name="The Palmyrah House", city="Mannar", district="Mannar", accommodation_type="Hotel",
         address="Mannar, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Agape", city="Mannar", district="Mannar", accommodation_type="Hotel",
         address="Mannar, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Victory's Gardens", city="Mannar", district="Mannar", accommodation_type="Guest House",
         address="Mannar, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="El Shaddai", city="Mannar", district="Mannar", accommodation_type="Guest House",
         address="Mannar, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Pesalai Beach View Hotel", city="Pesalai", district="Mannar", accommodation_type="Hotel",
         address="Pesalai, Mannar", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Mullaitivu ----------------
    dict(name="Mullai Villa Rest", city="Mullaitivu", district="Mullaitivu", accommodation_type="Bungalow",
         address="Thanneerootu West, Karaithuraipattu, Mullaitivu", registration_no="SLTDA/SQA/BUN/01130", licence_no="BUN/2026/0025", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Alai Resort", city="Mullaitivu", district="Mullaitivu", accommodation_type="Resort",
         address="Mullaitivu, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Sun & Sand Guest House", city="Mullaitivu", district="Mullaitivu", accommodation_type="Guest House",
         address="Mullaitivu, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Sunset Chalet", city="Mullaitivu", district="Mullaitivu", accommodation_type="Chalet",
         address="Mullaitivu, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Ocean Park Resort Mullaitivu", city="Mullaitivu", district="Mullaitivu", accommodation_type="Resort",
         address="Mullaitivu District, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Vavuniya ----------------
    dict(name="Green Park Resort", city="Vavuniya", district="Vavuniya", accommodation_type="Bungalow",
         address="Kandy Road, Meda Mawatha, Nawagama, Vavuniya", registration_no="SLTDA/SQA/BUN/01162", licence_no="BUN/2026/0024", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Ananthi Hotels", city="Vavuniya", district="Vavuniya", accommodation_type="Guest House",
         address="1st Lane, Sinnaputhukulam, Vavuniya", registration_no="SLTDA/SQA/GH/1055", licence_no="GH/2026/0403", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Hotel Oviya", city="Vavuniya", district="Vavuniya", accommodation_type="Hotel",
         address="Vavuniya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Nelly Star Hotel", city="Vavuniya", district="Vavuniya", accommodation_type="Hotel",
         address="Vavuniya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Thilaka Hotel", city="Vavuniya", district="Vavuniya", accommodation_type="Hotel",
         address="Vavuniya, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Batticaloa ----------------
    dict(name="Uga Bay", city="Pasikuda", district="Batticaloa", accommodation_type="Resort",
         address="Pasikuda, Batticaloa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Maalu Maalu Resort & Spa", city="Pasikuda", district="Batticaloa", accommodation_type="Resort",
         address="Pasikuda, Batticaloa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Amethyst Resort Passikudah", city="Pasikuda", district="Batticaloa", accommodation_type="Resort",
         address="Pasikuda, Batticaloa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Sun Siyam Pasikudah", city="Pasikuda", district="Batticaloa", accommodation_type="Resort",
         address="Pasikuda, Batticaloa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Amaya Beach Passikudah", city="Pasikuda", district="Batticaloa", accommodation_type="Resort",
         address="Pasikuda, Batticaloa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Ampara ----------------
    dict(name="Jetwing Surf", city="Arugam Bay", district="Ampara", accommodation_type="Hotel",
         address="Arugam Bay, Ampara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Kottukal Beach House by Jetwing", city="Pottuvil", district="Ampara", accommodation_type="Boutique Villa",
         address="Pottuvil, Ampara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Paper Moon Kudils", city="Arugam Bay", district="Ampara", accommodation_type="Resort",
         address="Arugam Bay, Ampara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Arugambay Roccos", city="Arugam Bay", district="Ampara", accommodation_type="Hotel",
         address="Arugam Bay, Ampara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="The Blue Wave Hotel", city="Arugam Bay", district="Ampara", accommodation_type="Hotel",
         address="Arugam Bay, Ampara", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Trincomalee ----------------
    dict(name="Nilaveli Beach Hotel", city="Nilaveli", district="Trincomalee", accommodation_type="Hotel",
         address="11th Mile Post, Nilaveli, Trincomalee", registration_no="SLTDA/SQA/HC/049", licence_no="HC/2026/0079", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Trinco Blu by Cinnamon", city="Trincomalee", district="Trincomalee", accommodation_type="Hotel",
         address="Trincomalee, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Uga Jungle Beach", city="Kuchchaveli", district="Trincomalee", accommodation_type="Resort",
         address="Kuchchaveli, Trincomalee", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Amaranthe Bay Resort & Spa", city="Trincomalee", district="Trincomalee", accommodation_type="Resort",
         address="Trincomalee, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Pigeon Island Beach Resort", city="Nilaveli", district="Trincomalee", accommodation_type="Resort",
         address="Nilaveli, Trincomalee", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Kurunegala ----------------
    dict(name="Kandyan Reach Hotel", city="Kurunegala", district="Kurunegala", accommodation_type="Hotel",
         address="Kurunegala, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Blue Sky", city="Kurunegala", district="Kurunegala", accommodation_type="Hotel",
         address="Kurunegala, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Janara", city="Kurunegala", district="Kurunegala", accommodation_type="Hotel",
         address="Kurunegala, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="The Epitome", city="Kurunegala", district="Kurunegala", accommodation_type="Hotel",
         address="Kurunegala District, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Rivendell Twisted Tree", city="Kurunegala", district="Kurunegala", accommodation_type="Resort",
         address="Kurunegala District, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Puttalam ----------------
    dict(name="Anantaya Resort & Spa Chilaw", city="Chilaw", district="Puttalam", accommodation_type="Resort",
         address="Chilaw, Puttalam", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Club Palm Bay", city="Marawila", district="Puttalam", accommodation_type="Resort",
         address="Marawila, Puttalam", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Carolina Beach Hotel", city="Chilaw", district="Puttalam", accommodation_type="Hotel",
         address="Chilaw, Puttalam", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Dolphin Beach Resort", city="Kalpitiya", district="Puttalam", accommodation_type="Resort",
         address="Kalpitiya, Puttalam", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Bar Reef Resort", city="Kalpitiya", district="Puttalam", accommodation_type="Resort",
         address="Kalpitiya, Puttalam", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Anuradhapura ----------------
    dict(name="Rajarata Hotel", city="Anuradhapura", district="Anuradhapura", accommodation_type="Hotel",
         address="Anuradhapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Heritage Hotel Anuradhapura", city="Anuradhapura", district="Anuradhapura", accommodation_type="Hotel",
         address="Anuradhapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Miridiya Lake Resort", city="Anuradhapura", district="Anuradhapura", accommodation_type="Resort",
         address="Anuradhapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="The Lakeside at Nuwarawewa", city="Anuradhapura", district="Anuradhapura", accommodation_type="Hotel",
         address="Anuradhapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Alakamanda", city="Anuradhapura", district="Anuradhapura", accommodation_type="Hotel",
         address="Anuradhapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Polonnaruwa ----------------
    dict(name="Hotel Sudu Araliya", city="Polonnaruwa", district="Polonnaruwa", accommodation_type="Hotel",
         address="New Town, Polonnaruwa", registration_no="SLTDA/SQA/TH/124", licence_no="TH/2026/0073", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="EKHO Lake House", city="Polonnaruwa", district="Polonnaruwa", accommodation_type="Hotel",
         address="Polonnaruwa, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Giritale Hotel", city="Giritale", district="Polonnaruwa", accommodation_type="Hotel",
         address="Giritale, Polonnaruwa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Deer Park Hotel", city="Giritale", district="Polonnaruwa", accommodation_type="Hotel",
         address="Giritale, Polonnaruwa", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Mahanuge", city="Polonnaruwa", district="Polonnaruwa", accommodation_type="Hotel",
         address="Polonnaruwa, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Badulla ----------------
    dict(name="98 Acres Resort & Spa", city="Ella", district="Badulla", accommodation_type="Resort",
         address="Ella, Badulla", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="EKHO Ella", city="Ella", district="Badulla", accommodation_type="Hotel",
         address="Ella, Badulla", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Oak Ray Ella Gap Hotel", city="Ella", district="Badulla", accommodation_type="Hotel",
         address="Ella, Badulla", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Morning Dew Boutique Hotel Ella", city="Ella", district="Badulla", accommodation_type="Boutique Hotel",
         address="Ella, Badulla", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="The Secret Ella", city="Ella", district="Badulla", accommodation_type="Hotel",
         address="Ella, Badulla", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Monaragala ----------------
    dict(name="Victory Inn", city="Monaragala", district="Monaragala", accommodation_type="Guest House",
         address="Wellawaya Road, Monaragala", registration_no="SLTDA/SQA/GH/0147", licence_no="GH/2026/0022", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Evergreen Park", city="Monaragala", district="Monaragala", accommodation_type="Guest House",
         address="Aliyawaththa, Monaragala", registration_no="SLTDA/SQA/GH/02127", licence_no="GH/2026/0608", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Hotel Divine Light Monaragala", city="Monaragala", district="Monaragala", accommodation_type="Hotel",
         address="Monaragala, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Gangana Resort Inn", city="Monaragala", district="Monaragala", accommodation_type="Hotel",
         address="Monaragala, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="The Grand Pearl Resort", city="Monaragala", district="Monaragala", accommodation_type="Resort",
         address="Monaragala, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Ratnapura ----------------
    dict(name="Grand Udawalawe Safari Resort", city="Udawalawe", district="Ratnapura", accommodation_type="Resort",
         address="Thanamalvila Road, Udawalawe", registration_no="SLTDA/SQA/HC/00192", licence_no="HC/2026/052", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="Centauria Hill Resort", city="Ratnapura", district="Ratnapura", accommodation_type="Resort",
         address="Ratnapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Lake Serenity Resort & Spa", city="Kuruwita", district="Ratnapura", accommodation_type="Resort",
         address="Kuruwita, Ratnapura", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Sapphire Holiday Resort", city="Ratnapura", district="Ratnapura", accommodation_type="Resort",
         address="Ratnapura, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Boulder Garden", city="Kalawana", district="Ratnapura", accommodation_type="Resort",
         address="Kalawana, Ratnapura", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),

    # ---------------- Kegalle ----------------
    dict(name="Rosyth Estate House", city="Kegalle", district="Kegalle", accommodation_type="Boutique Hotel",
         address="Kegalle, Sri Lanka", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Elephant Bay", city="Pinnawala", district="Kegalle", accommodation_type="Hotel",
         address="Pinnawala, Kegalle", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Hotel Elephant Park", city="Pinnawala", district="Kegalle", accommodation_type="Hotel",
         address="Pinnawala, Kegalle", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
    dict(name="Green Leaves Garden", city="Mawanella", district="Kegalle", accommodation_type="Home Stay",
         address="Aranayaka Road, Godagama, Mawanella", registration_no="SLTDA/SQA/HSU/00730", licence_no="HSU/2026/0003", source="Sri Lanka Tourism / SLTDA indexed record (2026)"),
    dict(name="The Grand Walawwa", city="Pinnawala", district="Kegalle", accommodation_type="Hotel",
         address="Pinnawala, Kegalle", registration_no=None, licence_no=None, source="Current public accommodation listing (2026)"),
]


def validate_dataset():
    """Fail early if district coverage or duplicate names are wrong."""
    counts = {}
    seen_names = set()

    for item in HOTELS:
        district = item["district"]
        counts[district] = counts.get(district, 0) + 1

        key = item["name"].strip().lower()
        if key in seen_names:
            raise ValueError(f"Duplicate accommodation name found: {item['name']}")
        seen_names.add(key)

    expected = set(PROVINCES)
    actual = set(counts)

    missing = expected - actual
    unexpected = actual - expected

    if missing:
        raise ValueError(f"Missing districts: {sorted(missing)}")
    if unexpected:
        raise ValueError(f"Unexpected districts: {sorted(unexpected)}")

    wrong_counts = {d: c for d, c in counts.items() if c < 5}
    if wrong_counts:
        raise ValueError(f"Districts with fewer than 5 records: {wrong_counts}")

    print(f"Dataset validation OK: {len(HOTELS)} accommodation records")
    print("District coverage:")
    for district in sorted(counts):
        print(f"  {district}: {counts[district]}")


def seed():
    validate_dataset()

    db = SessionLocal()

    try:
        # Create/reuse City rows based on the actual town/city label in each record.
        city_cache = {}

        for item in HOTELS:
            city_name = item["city"]
            district = item["district"]
            province = PROVINCES[district]

            key = (city_name.lower(), district.lower())

            if key not in city_cache:
                city = (
                    db.query(City)
                    .filter(City.name == city_name, City.district == district)
                    .first()
                )

                if city is None:
                    city = City(
                        name=city_name,
                        district=district,
                        province=province,
                    )
                    db.add(city)
                    db.flush()

                city_cache[key] = city

            # Idempotent seed:
            # if same hotel name + district already exists, skip it.
            existing = (
                db.query(Hotel)
                .filter(
                    Hotel.name == item["name"],
                    Hotel.district == district,
                )
                .first()
            )

            if existing:
                print(f"SKIP: {item['name']} ({district})")
                continue

            city = city_cache[key]

            hotel = Hotel(
                name=item["name"],
                address=item["address"],
                description=f"Real accommodation establishment in {district} District, Sri Lanka.",
                district=district,
                accommodation_type=item["accommodation_type"],
                registration_no=item["registration_no"],
                licence_no=item["licence_no"],
                source=item["source"],
                price_per_night=None,
                rating=None,
                available=True,
                city_id=city.id,
            )

            db.add(hotel)
            print(f"ADD : {item['name']} ({district})")

        db.commit()

        total = db.query(Hotel).count()
        print()
        print("Seed completed successfully.")
        print(f"Total hotels/accommodation records currently in database: {total}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
