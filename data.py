from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
import requests
from requests.exceptions import RequestException
import time

# ---------------- Logging Setup ----------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------- Flask App ----------------
app = Flask(__name__)

# ---------------- MongoDB Configuration ----------------
MONGODB_URI = "mongodb+srv://mandadivarunreddy:varunreddy2004@cluster2.lizqe.mongodb.net/"
DATABASE_NAME = "india_travel"
COLLECTION_NAME = "states"

# ---------------- Database Connection ----------------
def connect_to_mongodb():
    try:
        logger.info("Attempting to connect to MongoDB")
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        client.admin.command('ping')
        logger.info("Connected to MongoDB successfully")

        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        return client, db, collection

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None, None, None
    except Exception as e:
        logger.critical(f"Unexpected MongoDB error: {e}")
        return None, None, None

# ---------------- Image URL Validation ----------------
def validate_image_url(url):
    try:
        # Just check the head to avoid downloading the entire image
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except RequestException:
        return False
# Complete Indian States Data Structure
# This includes all 28 states with comprehensive tourism information

indian_states_data = {
    # SOUTH INDIA
    "andhra_pradesh": {
        "name": "Andhra Pradesh",
        "capital": "Amaravati",
        "region": "south",
        "coordinates": {"lat": 15.9129, "lng": 79.7400},
        "description": "Andhra Pradesh, located on the southeastern coast of India, is renowned for its rich cultural heritage, magnificent temples, and diverse landscapes. The state is the birthplace of the classical dance form Kuchipudi and boasts a vibrant tradition of arts, crafts, and cuisine. From the ancient Buddhist sites of Amaravati to the bustling port city of Visakhapatnam, Andhra Pradesh offers a perfect blend of history, spirituality, and natural beauty. The state is also famous for its spicy cuisine, handloom textiles, and warm hospitality.",
        "image": "https://unsplash.com/photos/river-near-rock-formations-6Z5px-pp3C0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Tirupati Balaji Temple", "Araku Valley", "Borra Caves", "Visakhapatnam Beaches",
            "Amaravati Buddhist Sites", "Srisailam Temple", "Horsley Hills", "Lepakshi Temple",
            "Gandikota Fort", "Belum Caves", "Papikondalu",
            "Chandragiri Fort", "Puttaparthi", "Kurnool Fort"
        ],
        "cuisine": [
            "Andhra Biryani", "Gongura Pachadi", "Pulihora", "Pesarattu", "Pootharekulu",
            "Gutti Vankaya", "Royyala Iguru", "Bobbatlu", "Andhra Fish Curry", "Avakaya Pickle"
        ],
        "culture": "Andhra Pradesh's culture is deeply rooted in classical traditions, with Kuchipudi dance being its most celebrated art form. The state celebrates festivals like Ugadi, Sankranti, and Brahmotsavam with great fervor. Telugu literature and cinema have flourished here, contributing significantly to South Indian culture.",
        "bestTimeToVisit": "October to March offers pleasant weather. April to June can be extremely hot, while July to September brings monsoons that enhance the natural beauty of hill stations like Araku Valley.",
        "transportation": "Well-connected by air through Visakhapatnam, Vijayawada, and Tirupati airports. Extensive railway network connects major cities. Road connectivity is excellent with National Highways connecting all major destinations.",
        "highlights": [
            "World-famous Tirupati Balaji Temple",
            "Scenic Araku Valley coffee plantations",
            "Ancient Amaravati Buddhist heritage",
            "Beautiful beaches of Visakhapatnam",
            "Spectacular Gandikota Grand Canyon"
        ]
    },

    "karnataka": {
        "name": "Karnataka",
        "capital": "Bengaluru",
        "region": "south",
        "coordinates": {"lat": 15.3173, "lng": 75.7139},
        "description": "Karnataka, the land of sandalwood and silk, is a treasure trove of architectural marvels, natural wonders, and technological innovation. From the cosmopolitan IT hub of Bengaluru to the royal grandeur of Mysore, the state offers incredible diversity. The magnificent ruins of Hampi, the pristine beaches of coastal Karnataka, and the lush Western Ghats make it a paradise for travelers. Karnataka is also renowned for its classical music tradition, exquisite handicrafts, and rich culinary heritage.",
        "image": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Hampi", "Mysore Palace", "Coorg", "Gokarna", "Chikmagalur", "Bandipur National Park",
            "Belur and Halebidu", "Badami Caves", "Jog Falls", "Udupi", "Shravanabelagola",
            "Chitradurga Fort", "Bijapur", "Dandeli Wildlife Sanctuary", "Nandi Hills"
        ],
        "cuisine": [
            "Masala Dosa", "Bisi Bele Bath", "Mysore Pak", "Dharwad Peda", "Neer Dosa",
            "Ragi Mudde", "Jolada Rotti", "Kokum Curry", "Chiroti", "Holige"
        ],
        "culture": "Karnataka has a rich tradition of classical music and dance, being the birthplace of several renowned musicians. The state celebrates Dussehra with grandeur, especially in Mysore. Yakshagana, a traditional theater form, is unique to Karnataka.",
        "bestTimeToVisit": "October to March is ideal for most regions. Hill stations like Coorg and Chikmagalur are pleasant year-round. Coastal areas are best visited from October to February.",
        "transportation": "Bengaluru serves as the main aviation hub. Excellent railway connectivity links major cities. State transport and private buses provide good road connectivity.",
        "highlights": [
            "UNESCO World Heritage Site of Hampi",
            "Royal splendor of Mysore Palace",
            "Coffee plantations of Coorg and Chikmagalur",
            "Pristine beaches of Gokarna and Udupi",
            "Wildlife sanctuaries and national parks"
        ]
    },

    "kerala": {
        "name": "Kerala",
        "capital": "Thiruvananthapuram",
        "region": "south",
        "coordinates": {"lat": 10.8505, "lng": 76.2711},
        "description": "Kerala, aptly called 'God's Own Country,' is a tropical paradise known for its serene backwaters, lush hill stations, pristine beaches, and rich cultural heritage. The state offers a unique blend of natural beauty and traditional arts, with Ayurveda, Kathakali, and Kalaripayattu being integral parts of its identity. From the tranquil houseboats of Alleppey to the spice plantations of Munnar, Kerala provides a rejuvenating experience for travelers seeking both adventure and relaxation.",
        "image": "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Alleppey Backwaters", "Munnar", "Thekkady", "Kovalam Beach", "Wayanad",
            "Kumarakom", "Varkala", "Kochi", "Athirappilly Falls", "Bekal Fort",
            "Periyar Wildlife Sanctuary", "Thrissur", "Kozhikode", "Vagamon", "Nelliampathy Hills"
        ],
        "cuisine": [
            "Kerala Fish Curry", "Appam with Stew", "Puttu and Kadala", "Sadhya", "Karimeen Fry",
            "Thalassery Biryani", "Ela Ada", "Payasam", "Meen Moilee", "Beef Roast"
        ],
        "culture": "Kerala's culture is distinguished by its classical arts like Kathakali, Mohiniyattam, and Kalaripayattu. The state has a high literacy rate and celebrates festivals like Onam and Thrissur Pooram with great enthusiasm. Traditional architecture, Ayurvedic medicine, and spice trade heritage define its cultural landscape.",
        "bestTimeToVisit": "October to March offers the most pleasant weather. Monsoon season (June-September) brings heavy rains but creates spectacular green landscapes.",
        "transportation": "Three international airports at Kochi, Thiruvananthapuram, and Kozhikode. Well-connected railway network and excellent road infrastructure including scenic routes through the Western Ghats.",
        "highlights": [
            "Enchanting backwater cruises in houseboats",
            "Picturesque hill station of Munnar",
            "Traditional Ayurvedic treatments and spas",
            "Vibrant cultural performances and festivals",
            "Rich biodiversity in wildlife sanctuaries"
        ]
    },

    "tamil_nadu": {
        "name": "Tamil Nadu",
        "capital": "Chennai",
        "region": "south",
        "coordinates": {"lat": 11.1271, "lng": 78.6569},
        "description": "Tamil Nadu, the cradle of Dravidian culture, is renowned for its magnificent temples, classical arts, and rich literary tradition. The state boasts some of India's most spectacular temple architecture, from the towering gopurams of Madurai to the rock-cut caves of Mahabalipuram. With a coastline stretching over 1,000 kilometers, hill stations like Ooty and Kodaikanal, and vibrant cities like Chennai, Tamil Nadu offers a perfect blend of spirituality, history, and natural beauty.",
        "image": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Meenakshi Temple Madurai", "Mahabalipuram", "Ooty", "Kodaikanal", "Rameswaram",
            "Kanyakumari", "Thanjavur", "Pondicherry", "Yercaud", "Chidambaram",
            "Tiruvannamalai", "Courtallam Falls", "Hogenakkal Falls", "Chettinad", "Kumbakonam"
        ],
        "cuisine": [
            "Chettinad Cuisine", "Sambar and Rasam", "Idli and Dosa", "Tamil Nadu Meals", "Pongal",
            "Murukku", "Adhirasam", "Filter Coffee", "Banana Leaf Meals", "Kozhukattai"
        ],
        "culture": "Tamil Nadu is the heartland of Tamil culture with a 2,000-year-old literary tradition. Classical dance forms like Bharatanatyam originated here. The state is famous for its temple festivals, classical music, and traditional crafts like Kanchipuram silk and Tanjore paintings.",
        "bestTimeToVisit": "November to March is ideal for most destinations. Hill stations are pleasant year-round. April to June can be very hot, while the monsoon season brings relief and greenery.",
        "transportation": "Chennai serves as the major transportation hub with international airport and extensive railway connections. Good road network connects all major tourist destinations.",
        "highlights": [
            "Architectural marvels of Dravidian temples",
            "UNESCO World Heritage Sites of Mahabalipuram and Thanjavur",
            "Scenic hill stations of Ooty and Kodaikanal",
            "Rich tradition of classical music and dance",
            "Spiritual significance of temples and pilgrimage sites"
        ]
    },

    # NORTH INDIA
    "delhi": {
        "name": "Delhi",
        "capital": "New Delhi",
        "region": "north",
        "coordinates": {"lat": 28.7041, "lng": 77.1025},
        "description": "Delhi, the capital territory of India, is a magnificent blend of ancient heritage and modernity. From the historic Red Fort and Jama Masjid to the contemporary structures of New Delhi, the city narrates the story of India's evolution. As the political and cultural heart of the nation, Delhi offers world-class museums, vibrant markets, diverse cuisine, and architectural marvels spanning different eras. The city serves as a gateway to exploring North India's rich heritage.",
        "image": "https://images.unsplash.com/photo-1586963631019-1dd4e0c62ed3?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Red Fort", "India Gate", "Qutub Minar", "Humayun's Tomb", "Lotus Temple",
            "Akshardham Temple", "Chandni Chowk", "Raj Ghat", "Jama Masjid", "Lodhi Gardens",
            "National Museum", "Purana Qila", "Jantar Mantar", "Tughlaqabad Fort", "Hauz Khas Village"
        ],
        "cuisine": [
            "Chole Bhature", "Paranthas", "Delhi Chaat", "Butter Chicken", "Rajma Chawal",
            "Kulfi", "Nihari", "Kebabs", "Aloo Tikki", "Jalebi"
        ],
        "culture": "Delhi's culture is a melting pot of various traditions, reflecting its status as India's capital. The city celebrates all major festivals with equal enthusiasm and is known for its vibrant street food culture, historical monuments, and contemporary arts scene.",
        "bestTimeToVisit": "October to March offers pleasant weather. Summers (April-June) can be extremely hot, while monsoons bring moderate relief.",
        "transportation": "Excellent connectivity via metro, buses, and taxis. Indira Gandhi International Airport connects to major global destinations. Multiple railway stations serve different regions of India.",
        "highlights": [
            "UNESCO World Heritage Sites including Red Fort and Qutub Minar",
            "Vibrant street food and shopping markets",
            "Political and cultural center of India",
            "Museums and art galleries showcasing Indian heritage",
            "Modern infrastructure and metro connectivity"
        ]
    },

    "haryana": {
        "name": "Haryana",
        "capital": "Chandigarh",
        "region": "north",
        "coordinates": {"lat": 29.0588, "lng": 76.0856},
        "description": "Haryana, surrounding Delhi on three sides, is known as the 'Land of Rotis' and is steeped in mythological significance as the land of the Mahabharata. The state is renowned for its agricultural prosperity, vibrant folk culture, and historical significance. From the ancient Kurukshetra to the modern planned city of Gurugram, Haryana represents both tradition and progress. The state is famous for its warm hospitality, traditional wrestling culture, and delicious North Indian cuisine.",
        "image": "https://images.unsplash.com/photo-1587474260584-136574528ed5?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Kurukshetra", "Panipat", "Faridabad", "Gurugram", "Ambala", "Karnal",
            "Pinjore Gardens", "Morni Hills", "Sultanpur Bird Sanctuary", "Badkhal Lake",
            "Brahma Sarovar", "Sannihit Sarovar", "Tilyar Lake", "Karna Lake", "Surajkund"
        ],
        "cuisine": [
            "Bajra Khichdi", "Kadhi Pakora", "Churma", "Besan Masala Roti", "Haryanvi Lassi",
            "Singri ki Sabzi", "Bathua Raita", "Methi Gajar", "Kheer", "Ghevar"
        ],
        "culture": "Haryana's culture is deeply rooted in its agricultural heritage and mythological significance. The state is famous for its folk dances like Ghoomar and Sapera, traditional wrestling (Kushti), and festivals like Teej and Karva Chauth.",
        "bestTimeToVisit": "October to March is the best time to visit. Summers can be quite hot, while winters are pleasant and ideal for sightseeing.",
        "transportation": "Well-connected by road and rail to Delhi and other major cities. The state has good highway connectivity and is served by Delhi's airport.",
        "highlights": [
            "Kurukshetra - Land of the Mahabharata",
            "Modern industrial and IT hub of Gurugram",
            "Rich agricultural and dairy farming traditions",
            "Traditional wrestling and sports culture",
            "Proximity to Delhi making it easily accessible"
        ]
    },

    "himachal_pradesh": {
        "name": "Himachal Pradesh",
        "capital": "Shimla",
        "region": "north",
        "coordinates": {"lat": 31.1048, "lng": 77.1734},
        "description": "Himachal Pradesh, nestled in the lap of the Himalayas, is a paradise for nature lovers and adventure enthusiasts. Known as 'Dev Bhoomi' (Land of Gods), the state offers breathtaking landscapes, snow-capped peaks, verdant valleys, and spiritual tranquility. From the colonial charm of Shimla to the adventure sports in Manali, from the spiritual serenity of Dharamshala to the remote beauty of Spiti Valley, Himachal Pradesh provides diverse experiences for every traveler.",
        "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Shimla", "Manali", "Dharamshala", "Dalhousie", "Kasauli", "Kullu", "Spiti Valley",
            "Kinnaur", "Chamba", "McLeod Ganj", "Solang Valley", "Rohtang Pass", "Khajjiar",
            "Kufri", "Narkanda", "Bir Billing", "Tirthan Valley", "Chitkul", "Kalpa", "Malana"
        ],
        "cuisine": [
            "Dham", "Chana Madra", "Rajma", "Khatta", "Babru", "Aktori", "Kullu Trout",
            "Sidu", "Patande", "Mittha", "Chha Gosht", "Tudkiya Bhath"
        ],
        "culture": "Himachal Pradesh has a rich cultural heritage with influences from both Hindu and Buddhist traditions. The state is known for its colorful festivals, traditional folk dances, handicrafts, and warm hospitality of mountain people.",
        "bestTimeToVisit": "March to June for summers, October to February for winter sports and snow. Monsoon season (July-September) should be avoided due to landslides.",
        "transportation": "Accessible by road from Delhi and other major cities. Kalka-Shimla railway offers scenic journey. Nearest airports are in Chandigarh and Dharamshala.",
        "highlights": [
            "Scenic hill stations and mountain resorts",
            "Adventure sports and trekking opportunities",
            "Buddhist monasteries and spiritual retreats",
            "Colonial architecture and heritage hotels",
            "Apple orchards and natural beauty"
        ]
    },

    "jammu_kashmir": {
        "name": "Jammu and Kashmir",
        "capital": "Srinagar (Summer), Jammu (Winter)",
        "region": "north",
        "coordinates": {"lat": 34.0837, "lng": 74.7973},
        "description": "Jammu and Kashmir, often called 'Paradise on Earth,' is renowned for its stunning natural beauty, pristine lakes, snow-capped mountains, and rich cultural heritage. The region offers diverse experiences from the Dal Lake's tranquil houseboats in Srinagar to the spiritual temples of Jammu, and from the adventurous treks in Ladakh to the meadows of Gulmarg. The state is famous for its handicrafts, saffron, and warm hospitality.",
        "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Srinagar", "Gulmarg", "Pahalgam", "Jammu", "Vaishno Devi", "Sonamarg", "Leh",
            "Kargil", "Amarnath Cave", "Patnitop", "Dachigam National Park", "Hemis Monastery",
            "Khardung La", "Nubra Valley", "Pangong Tso", "Magnetic Hill", "Shanti Stupa"
        ],
        "cuisine": [
            "Rogan Josh", "Yakhni", "Dum Aloo", "Rajma", "Haak", "Modur Pulav", "Sheermal",
            "Phirni", "Kahwa", "Noon Chai", "Tabak Maaz", "Gustaba", "Harissa"
        ],
        "culture": "The culture of J&K is a beautiful amalgamation of Hindu, Buddhist, and Islamic traditions. The region is known for its handicrafts, carpets, shawls, and traditional music and dance forms.",
        "bestTimeToVisit": "April to October for Kashmir Valley, October to March for Jammu region. Ladakh is accessible from May to September.",
        "transportation": "Srinagar and Jammu airports connect to major Indian cities. Road connectivity via National Highway 44. Rail connectivity available up to Jammu.",
        "highlights": [
            "Breathtaking landscapes and natural beauty",
            "Houseboat stays on Dal Lake",
            "Adventure sports and trekking",
            "Ancient temples and monasteries",
            "Famous handicrafts and saffron"
        ]
    },

    "punjab": {
        "name": "Punjab",
        "capital": "Chandigarh",
        "region": "north",
        "coordinates": {"lat": 31.1471, "lng": 75.3412},
        "description": "Punjab, the 'Land of Five Rivers,' is known for its rich agricultural heritage, vibrant Sikh culture, and warm hospitality. The state is famous for the Golden Temple in Amritsar, one of the most revered Sikh shrines. Punjab's fertile plains, colorful festivals, energetic Bhangra dance, and delicious cuisine make it a culturally rich destination. The state played a crucial role in India's independence movement and Green Revolution.",
        "image": "https://images.unsplash.com/photo-1544531585-bb8b419e4b23?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Golden Temple Amritsar", "Jallianwala Bagh", "Wagah Border", "Anandpur Sahib",
            "Patiala", "Ludhiana", "Jalandhar", "Bathinda", "Fatehgarh Sahib", "Kapurthala",
            "Ropar", "Muktsar", "Pathankot", "Mohali", "Chandigarh"
        ],
        "cuisine": [
            "Makki di Roti and Sarson da Saag", "Butter Chicken", "Rajma Chawal", "Chole Bhature",
            "Amritsari Kulcha", "Lassi", "Pinni", "Jalebi", "Paratha", "Dal Makhani"
        ],
        "culture": "Punjab's culture is deeply influenced by Sikhism, with gurudwaras playing a central role. The state is famous for Bhangra and Giddha folk dances, vibrant festivals like Baisakhi, and its tradition of hospitality and community service.",
        "bestTimeToVisit": "October to March offers pleasant weather. Avoid summer months (April-June) due to extreme heat.",
        "transportation": "Well-connected by air, rail, and road. Amritsar and Ludhiana have airports. Excellent railway network connects major cities.",
        "highlights": [
            "Golden Temple - holiest Sikh shrine",
            "Wagah Border ceremony",
            "Rich agricultural heritage",
            "Vibrant festivals and folk culture",
            "Historical significance in independence movement"
        ]
    },

    "rajasthan": {
        "name": "Rajasthan",
        "capital": "Jaipur",
        "region": "north",
        "coordinates": {"lat": 27.0238, "lng": 74.2179},
        "description": "Rajasthan, the 'Land of Kings,' is India's largest state and a magnificent showcase of royal heritage, desert landscapes, and vibrant culture. From the pink palaces of Jaipur to the golden sands of Jaisalmer, from the romantic lakes of Udaipur to the blue houses of Jodhpur, Rajasthan offers a fairy-tale experience. The state is renowned for its magnificent forts, opulent palaces, colorful festivals, traditional arts and crafts, and desert adventures.",
        "image": "https://images.unsplash.com/photo-1477587458883-47145ed94245?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Jaipur", "Udaipur", "Jodhpur", "Jaisalmer", "Pushkar", "Mount Abu", "Bikaner",
            "Ajmer", "Chittorgarh", "Ranthambore", "Bharatpur", "Kota", "Bundi", "Shekhawati",
            "Mandawa", "Alwar", "Sawai Madhopur", "Jhalawar", "Dungarpur", "Banswara"
        ],
        "cuisine": [
            "Dal Baati Churma", "Laal Maas", "Gatte ki Sabzi", "Ker Sangri", "Pyaaz Kachori",
            "Mawa Kachori", "Ghevar", "Rasgulla", "Mirchi Bada", "Rajasthani Thali"
        ],
        "culture": "Rajasthan's culture is a magnificent blend of royal traditions, folk arts, and desert lifestyle. The state is famous for its folk dances like Ghoomar and Kalbelia, traditional music, puppet shows, and colorful festivals.",
        "bestTimeToVisit": "October to March is ideal. Summers (April-June) can be extremely hot, especially in desert areas.",
        "transportation": "Well-connected by air, rail, and road. Major cities have airports. Excellent railway network including luxury trains like Palace on Wheels.",
        "highlights": [
            "Magnificent forts and palaces",
            "Thar Desert experiences and camel safaris",
            "Colorful festivals and folk performances",
            "Traditional handicrafts and textiles",
            "Wildlife sanctuaries and national parks"
        ]
    },

    "uttarakhand": {
        "name": "Uttarakhand",
        "capital": "Dehradun",
        "region": "north",
        "coordinates": {"lat": 30.0668, "lng": 79.0193},
        "description": "Uttarakhand, known as 'Devbhoomi' (Land of Gods), is a paradise for spiritual seekers, adventure enthusiasts, and nature lovers. The state encompasses the majestic Himalayas, sacred rivers, pristine lakes, and lush forests. From the spiritual significance of Rishikesh and Haridwar to the scenic beauty of hill stations like Nainital and Mussoorie, Uttarakhand offers diverse experiences. The state is also famous for its pilgrimage sites, yoga centers, and adventure sports.",
        "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Rishikesh", "Haridwar", "Nainital", "Mussoorie", "Dehradun", "Jim Corbett National Park",
            "Kedarnath", "Badrinath", "Gangotri", "Yamunotri", "Valley of Flowers", "Hemkund Sahib",
            "Auli", "Ranikhet", "Almora", "Kausani", "Lansdowne", "Chopta", "Binsar", "Munsiyari"
        ],
        "cuisine": [
            "Kumaoni Raita", "Bhatt ki Churkani", "Aloo ke Gutke", "Phaanu", "Chainsoo",
            "Jhangora Kheer", "Arsa", "Singal", "Kandalee ka Saag", "Madua ki Roti"
        ],
        "culture": "Uttarakhand's culture is deeply spiritual with strong traditions of yoga, meditation, and pilgrimage. The state is known for its folk dances, traditional music, and festivals celebrating the mountain way of life.",
        "bestTimeToVisit": "March to June and September to November. Winter months are ideal for lower altitude areas, while summer is best for high-altitude destinations.",
        "transportation": "Accessible by road from Delhi and other major cities. Nearest airports are Dehradun and Pantnagar. Railway connectivity available to major cities.",
        "highlights": [
            "Char Dham pilgrimage sites",
            "Adventure sports and trekking",
            "Yoga and meditation centers",
            "Wildlife sanctuaries and national parks",
            "Scenic hill stations and mountain views"
        ]
    },

    "uttar_pradesh": {
        "name": "Uttar Pradesh",
        "capital": "Lucknow",
        "region": "north",
        "coordinates": {"lat": 26.8467, "lng": 80.9462},
        "description": "Uttar Pradesh, India's most populous state, is a treasure trove of history, culture, and spirituality. Home to the iconic Taj Mahal, the sacred city of Varanasi, and the birthplace of Lord Krishna and Rama, the state holds immense religious and historical significance. From the Mughal architecture of Agra to the colonial charm of Lucknow, from the spiritual ghats of Varanasi to the Buddhist sites of Sarnath, UP offers an incredible journey through India's rich heritage.",
        "image": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Agra (Taj Mahal)", "Varanasi", "Lucknow", "Mathura", "Vrindavan", "Ayodhya",
            "Allahabad", "Sarnath", "Fatehpur Sikri", "Chitrakoot", "Dudhwa National Park",
            "Hastinapur", "Jhansi", "Kanpur", "Meerut", "Aligarh", "Bareilly", "Gorakhpur"
        ],
        "cuisine": [
            "Lucknowi Biryani", "Kebabs", "Tunday Kababi", "Petha", "Kulfi", "Malai Makhan",
            "Chaat", "Kachori", "Samosa", "Jaleba", "Rabri", "Balushahi"
        ],
        "culture": "UP's culture is a magnificent blend of Hindu, Muslim, and British influences. The state is famous for its classical music, dance, literature, and crafts. It's the heartland of Hindi language and literature.",
        "bestTimeToVisit": "October to March offers pleasant weather. Summers can be extremely hot, while monsoons bring moderate relief.",
        "transportation": "Excellent connectivity by air, rail, and road. Multiple airports serve major cities. Extensive railway network connects all parts of the state.",
        "highlights": [
            "Taj Mahal - Wonder of the World",
            "Spiritual significance of Varanasi",
            "Rich Mughal and British colonial heritage",
            "Birthplace of major Hindu deities",
            "Cultural capital of North India"
        ]
    },
        "west_bengal": {
        "name": "West Bengal",
        "capital": "Kolkata",
        "region": "east",
        "coordinates": {"lat": 22.9868, "lng": 87.8550},
        "description": "West Bengal, known for its rich cultural heritage and artistic legacy, is home to the vibrant city of Kolkata, the cultural capital of India. The state is famous for its literature, art, and festivals, including Durga Puja, which showcases the grandeur of Bengali culture. From the serene Sundarbans mangroves to the tea gardens of Darjeeling, West Bengal offers a diverse landscape and a rich culinary tradition.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Kolkata", "Darjeeling", "Sundarbans", "Kalimpong", "Shantiniketan","Singalila National Park"
            "Digha", "Murshidabad", "Howrah Bridge", "Victoria Memorial", "Siliguri"
        ],
        "cuisine": [
            "Bengali Fish Curry", "Macher Jhol", "Shorshe Ilish", "Mishti Doi", "Puchka",
            "Sandesh", "Chingri Malai Curry", "Luchi and Alur Dom", "Bengali Sweets", "Kosha Mangsho"
        ],
        "culture": "West Bengal's culture is a blend of various influences, with a strong emphasis on literature, music, and art. The state is known for its classical dance forms, folk traditions, and vibrant festivals, particularly the Durga Puja, which attracts visitors from all over the world.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Kolkata serves as the main transportation hub with an international airport. The state has a well-developed railway network and good road connectivity.",
        "highlights": [
            "Cultural richness of Kolkata",
            "Tea gardens of Darjeeling",
            "Biodiversity of Sundarbans",
            "Festivals like Durga Puja",
            "Historical sites and architecture"
        ]
    },

    "odisha": {
        "name": "Odisha",
        "capital": "Bhubaneswar",
        "region": "east",
        "coordinates": {"lat": 20.9517, "lng": 85.0985},
        "description": "Odisha, known for its ancient temples and rich cultural heritage, is home to the famous Jagannath Temple in Puri and the Sun Temple in Konark. The state boasts beautiful beaches, lush forests, and vibrant tribal culture. Odisha's art forms, including classical dance and handicrafts, reflect its rich traditions and history.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Puri", "Konark", "Bhubaneswar", "Cuttack", "Chilika Lake",
            "Simlipal National Park", "Udayagiri and Khandagiri Caves", "Bhitarkanika National Park", "Dhauli", "Khandagiri"
        ],
        "cuisine": [
            "Dalma", "Pakhala", "Rasgulla", "Chhena Poda", "Macha Jhola",
            "Kanika", "Badi Chura", "Dahi Pakhala", "Chhena Gaja", "Prawn Malai Curry"
        ],
        "culture": "Odisha's culture is characterized by its classical dance forms like Odissi, traditional music, and vibrant festivals. The state celebrates various festivals with great enthusiasm, showcasing its rich heritage and artistic traditions.",
        "bestTimeToVisit": "October to March is ideal for visiting, as the weather is pleasant. The summer months can be quite hot.",
        "transportation": "Bhubaneswar is well-connected by air, rail, and road. The city has an international airport and a good railway network.",
        "highlights": [
            "Jagannath Temple in Puri",
            "Sun Temple in Konark",
            "Rich tribal culture and handicrafts",
            "Beautiful beaches and lakes",
            "Classical dance and music traditions"
        ]
    },

    "bihar": {
        "name": "Bihar",
        "capital": "Patna",
        "region": "east",
        "coordinates": {"lat": 25.0961, "lng": 85.3131},
        "description": "Bihar, known for its historical significance, is the birthplace of Buddhism and home to ancient universities like Nalanda and Vikramshila. The state has a rich cultural heritage, with numerous temples, monuments, and festivals. Bihar's cuisine is diverse, with a variety of traditional dishes that reflect its agricultural roots.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Bodh Gaya", "Nalanda", "Patna", "Rajgir", "Vaishali",
            "Kushinagar", "Bihar Sharif", "Gaya", "Sonepur Mela", "Madhubani"
        ],
        "cuisine": [
            "Litti Chokha", "Sattu Paratha", "Chura Dahi", "Thekua", "Kadhi Badi",
            "Dal Puri", "Bihari Kebab", "Chura", "Mithila Cuisine", "Pitha"
        ],
        "culture": "Bihar's culture is deeply rooted in its historical significance, with a strong emphasis on education, literature, and spirituality. The state celebrates various festivals, including Chhath Puja, with great fervor.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. Summers can be extremely hot.",
        "transportation": "Patna serves as the main transportation hub with an airport and railway station. The state has good road connectivity.",
        "highlights": [
            "Historical significance of Bodh Gaya",
            "Ancient universities of Nalanda and Vikramshila",
            "Rich cultural heritage and festivals",
            "Diverse cuisine and traditional dishes",
            "Spiritual significance in Buddhism"
        ]
    },

    "assam": {
        "name": "Assam",
        "capital": "Dispur",
        "region": "east",
        "coordinates": {"lat": 26.2006, "lng": 92.9376},
        "description": "Assam, known for its tea gardens and rich biodiversity, is a state of stunning natural beauty. The Brahmaputra River flows through the state, providing fertile land for agriculture. Assam is famous for its wildlife, including the one-horned rhinoceros, and its vibrant culture, which includes traditional dance forms and festivals.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Kaziranga National Park", "Guwahati", "Majuli", "Tea Gardens", "Sivasagar",
            "Nameri National Park", "Manas National Park", "Hajo", "Tawang", "Jorhat"
        ],
        "cuisine": [
            "Assamese Thali", "Masor Tenga", "Khar", "Pitha", "Duck Meat Curry",
            "Aloo Pitika", "Baanhgajor Lagot Kukura", "Fish Tenga", "Chura Doi", "Laru"
        ],
        "culture": "Assam's culture is a blend of various ethnic groups, with a rich tradition of music, dance, and festivals. Bihu is the most celebrated festival, showcasing the state's vibrant culture and agricultural heritage.",
        "bestTimeToVisit": "October to April is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Guwahati is the main transportation hub with an international airport. The state has a good railway network and road connectivity.",
        "highlights": [
            "Kaziranga National Park and its wildlife",
            "Tea gardens and plantations",
            "Rich cultural heritage and festivals",
            "Brahmaputra River and river cruises",
            "Traditional Assamese cuisine"
        ]
    },

    "sikkim": {
        "name": "Sikkim",
        "capital": "Gangtok",
        "region": "east",
        "coordinates": {"lat": 27.5330, "lng": 88.5122},
        "description": "Sikkim, a small yet stunning state in the Himalayas, is known for its breathtaking landscapes, rich biodiversity, and vibrant culture. The state is home to the majestic Kanchenjunga, the third highest mountain in the world. Sikkim offers a unique blend of natural beauty, adventure, and spirituality, with numerous monasteries and trekking routes.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Gangtok", "Pelling", "Nathula Pass", "Zuluk", "Yuksom",
            "Khecheopalri Lake", "Rumtek Monastery", "Tsomgo Lake", "Namchi",
        ],
        "cuisine": [
            "Momos", "Thukpa", "Phagshapa", "Gundruk", "Sel Roti",
            "Chhurpi", "Sikkimese Thali", "Aloo Dum", "Fried Rice", "Pork Curry"
        ],
        "culture": "Sikkim's culture is a blend of various ethnic groups, including Lepchas, Bhutias, and Nepalis. The state is known for its vibrant festivals, traditional music, and dance forms, reflecting its rich heritage.",
        "bestTimeToVisit": "March to June and September to December are the best times to visit, as the weather is pleasant. Monsoon season (July-August) can bring heavy rains.",
        "transportation": "Gangtok is well-connected by road, and the nearest airport is in Pakyong. The state has a good road network for local travel.",
        "highlights": [
            "Breathtaking views of Kanchenjunga",
            "Rich biodiversity and trekking opportunities",
            "Cultural festivals and traditions",
            "Serene monasteries and spiritual retreats",
            "Delicious Sikkimese cuisine"
        ]
    },

    "tripura": {
        "name": "Tripura",
        "capital": "Agartala",
        "region": "east",
        "coordinates": {"lat": 23.9408, "lng": 91.9882},
        "description": "Tripura, a small state in the northeast, is known for its lush green hills, rich cultural heritage, and historical significance. The state is home to various ethnic communities and offers a unique blend of traditions, festivals, and cuisines. Tripura's natural beauty, including its lakes and forests, makes it a hidden gem in India.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Agartala", "Ujjayanta Palace", "Neermahal", "Sepahijala Wildlife Sanctuary", "Unakoti",
            "Jampui Hills", "Rudrasagar Lake", "Tripura Sundari Temple", "Bhuvaneshwari Temple", "Kailashahar"
        ],
        "cuisine": [
            "Mui Borok", "Panta Ilish", "Chakhwi", "Bhangui", "Fish Curry",
            "Pork with Bamboo Shoot", "Khar", "Chakol", "Macher Jhol", "Chutney"
        ],
        "culture": "Tripura's culture is a blend of various ethnic groups, with a rich tradition of music, dance, and festivals. The state celebrates various tribal festivals, showcasing its diverse heritage.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Agartala is well-connected by air and road. The state has a good road network for local travel.",
        "highlights": [
            "Rich cultural heritage and traditions",
            "Beautiful lakes and hills",
            "Historical significance and temples",
            "Diverse cuisine and tribal festivals",
            "Wildlife sanctuaries and natural beauty"
        ]
    },

    "manipur": {
        "name": "Manipur",
        "capital": "Imphal",
        "region": "east",
        "coordinates": {"lat": 24.6637, "lng": 93.9063},
        "description": "Manipur, known as the 'Jewel of India,' is famous for its rich culture, classical dance forms, and beautiful landscapes. The state is home to the picturesque Loktak Lake and the unique floating phumdis. Manipur's vibrant festivals, traditional crafts, and warm hospitality make it a captivating destination.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Imphal", "Loktak Lake", "Kangla Fort", "Shree Govindajee Temple", "Khonghampat Orchidarium",
            "Sangai Festival", "Kangla", "Moirang", "Tamenglong", "Churachandpur"
        ],
        "cuisine": [
            "Eromba", "Singju", "Kangshoi", "Ngari", "Chakhao Kheer",
            "Bai", "Khar", "Macher Ngari", "Paan", "Kangshoi"
        ],
        "culture": "Manipur's culture is rich in traditions, with a strong emphasis on dance, music, and festivals. The state is known for its classical dance form, Manipuri, and various tribal festivals that showcase its diverse heritage.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Imphal is well-connected by air and road. The state has a good road network for local travel.",
        "highlights": [
            "Beautiful Loktak Lake and floating phumdis",
            "Rich cultural heritage and traditions",
            "Classical dance forms and music",
            "Vibrant festivals and crafts",
            "Warm hospitality and local cuisine"
        ]
    },

    "nagaland": {
        "name": "Nagaland",
        "capital": "Kohima",
        "region": "east",
        "coordinates": {"lat": 26.1584, "lng": 94.5624},
        "description": "Nagaland, known for its rich tribal culture and vibrant festivals, is a state of stunning landscapes and diverse ethnic communities. The state is famous for its colorful festivals, traditional crafts, and warm hospitality. Nagaland's natural beauty, including hills and valleys, makes it a captivating destination.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Kohima", "Dimapur", "Wokha", "Mon", "Zunheboto",
            "Khonoma Village", "Dzukou Valley", "Kisama Heritage Village", "Naga Heritage Village", "Mokokchung"
        ],
        "cuisine": [
            "Smoked Pork with Bamboo Shoot", "Naga Chili", "Pork Curry", "Fish Curry", "Rice",
            "Kangshoi", "Zutho", "Naga Sausages", "Chutney", "Pitha"
        ],
        "culture": "Nagaland's culture is deeply rooted in its tribal heritage, with a strong emphasis on music, dance, and festivals. The state celebrates various tribal festivals, showcasing its vibrant traditions and crafts.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Kohima is well-connected by road. The nearest airport is in Dimapur, and the state has a good road network for local travel.",
        "highlights": [
            "Rich tribal culture and traditions",
            "Colorful festivals and crafts",
            "Stunning landscapes and natural beauty",
            "Warm hospitality and local cuisine",
            "Unique cultural experiences"
        ]
    },

    "arunachal_pradesh": {
        "name": "Arunachal Pradesh",
        "capital": "Itanagar",
        "region": "east",
        "coordinates": {"lat": 27.0950, "lng": 93.6168},
        "description": "Arunachal Pradesh, known as the 'Land of the Rising Sun,' is famous for its breathtaking landscapes, rich biodiversity, and vibrant tribal culture. The state is home to numerous rivers, mountains, and valleys, making it a paradise for nature lovers and adventure enthusiasts. Arunachal Pradesh's unique culture and traditions reflect its diverse ethnic communities.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Itanagar", "Tawang", "Ziro Valley", "Bomdila", "Dirang",
            "Sela Pass", "Namdapha National Park", "Pasighat", "Bhalukpong", "Mechuka"
        ],
        "cuisine": [
            "Thukpa", "Momos", "Pork with Bamboo Shoot", "Fish Curry", "Chura",
            "Khar", "Pitha", "Rice", "Chutney", "Pork Curry"
        ],
        "culture": "Arunachal Pradesh's culture is a blend of various tribal traditions, with a strong emphasis on music, dance, and festivals. The state celebrates various tribal festivals, showcasing its rich heritage and vibrant traditions.",
                "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Itanagar is well-connected by road. The nearest airport is in Tezpur, and the state has a good road network for local travel.",
        "highlights": [
            "Breathtaking landscapes and natural beauty",
            "Rich biodiversity and wildlife",
            "Vibrant tribal culture and traditions",
            "Adventure opportunities in trekking and river rafting",
            "Unique cultural experiences and festivals"
        ]
    },

    "meghalaya": {
        "name": "Meghalaya",
        "capital": "Shillong",
        "region": "east",
        "coordinates": {"lat": 25.4670, "lng": 91.3662},
        "description": "Meghalaya, known as the 'Abode of Clouds,' is famous for its stunning landscapes, lush green hills, and vibrant culture. The state is home to unique living root bridges, beautiful waterfalls, and rich biodiversity. Meghalaya's culture is influenced by its indigenous tribes, and the state celebrates various festivals with great enthusiasm.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Shillong", "Cherrapunji", "Mawlynnong", "Nohkalikai Falls", "Living Root Bridges",
            "Dawki", "Umiam Lake", "Laitlum Canyons", "Sohra", "Jowai"
        ],
        "cuisine": [
            "Jadoh", "Dohneiiong", "Pukhlein", "Bamboo Shoot Curry", "Khar",
            "Pork with Bamboo Shoot", "Fish Curry", "Chutney", "Rice", "Momos"
        ],
        "culture": "Meghalaya's culture is rich in traditions, with a strong emphasis on music, dance, and festivals. The state is known for its vibrant folk music and the famous Wangala festival.",
        "bestTimeToVisit": "October to April is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Shillong is well-connected by road and has an airport. The state has a good road network for local travel.",
        "highlights": [
            "Stunning landscapes and natural beauty",
            "Unique living root bridges",
            "Rich biodiversity and wildlife",
            "Vibrant tribal culture and festivals",
            "Adventure opportunities in trekking and caving"
        ]
    },

    "mizoram": {
        "name": "Mizoram",
        "capital": "Aizawl",
        "region": "east",
        "coordinates": {"lat": 23.1645, "lng": 92.9376},
        "description": "Mizoram, known for its rolling hills and vibrant culture, is a state of stunning natural beauty. The state is home to various ethnic communities and offers a unique blend of traditions, festivals, and cuisines. Mizoram's lush landscapes, including forests and rivers, make it a captivating destination.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Aizawl", "Lunglei", "Champhai", "Saitual", "Serchhip",
            "Mizoram State Museum", "Durtlang Hills", "Vantawng Falls", "Tam Dil", "Reiek"
        ],
        "cuisine": [
            "Bai", "Mizo Bamboo Shoot", "Vawksa Rep", "Khawchiar", "Mizo Fish Curry",
            "Chhum Han", "Pawndum", "Kawtchhiat", "Mizo Chicken Curry", "Kawtchhiat"
        ],
        "culture": "Mizoram's culture is rich in traditions, with a strong emphasis on music, dance, and festivals. The state celebrates various festivals, including Chapchar Kut and Pawl Kut, showcasing its vibrant heritage.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Aizawl is well-connected by road and has an airport. The state has a good road network for local travel.",
        "highlights": [
            "Stunning landscapes and natural beauty",
            "Rich cultural heritage and traditions",
            "Vibrant festivals and crafts",
            "Warm hospitality and local cuisine",
            "Unique cultural experiences"
        ]
    },

    "telangana": {
        "name": "Telangana",
        "capital": "Hyderabad",
        "region": "south",
        "coordinates": {"lat": 18.1124, "lng": 79.0193},
        "description": "Telangana, India's youngest state, is a perfect blend of historical grandeur and modern development. The state is home to the 'City of Pearls' - Hyderabad, known for its iconic Charminar, delicious biryani, and thriving IT industry. Rich in cultural heritage with magnificent forts, palaces, and temples, Telangana also boasts beautiful lakes, wildlife sanctuaries, and traditional crafts.",
        "image": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Charminar", "Golconda Fort", "Ramoji Film City", "Salar Jung Museum", "Hussain Sagar Lake",
            "Warangal Fort", "Thousand Pillar Temple", "Bhadrachalam", "Medak Cathedral", "Nagarjuna Sagar"
        ],
        "cuisine": [
            "Hyderabadi Biryani", "Haleem", "Karachi Biscuit", "Osmania Biscuit", "Qubani ka Meetha",
            "Lukhmi", "Nihari", "Keema", "Sheer Khurma", "Falooda"
        ],
        "culture": "Telangana's culture is a rich blend of Telugu traditions and Nizami heritage. The state is famous for its folk dances like Perini and Lambadi, handloom textiles, and festivals like Bonalu and Bathukamma.",
        "bestTimeToVisit": "October to March offers pleasant weather. Summer months can be quite hot, while monsoons bring relief and greenery.",
        "transportation": "Hyderabad International Airport connects to major global destinations. Excellent railway network and road connectivity within the state.",
        "highlights": [
            "Historic Charminar and Golconda Fort",
            "World's largest film studio complex - Ramoji Film City",
            "IT hub and modern infrastructure",
            "Famous Hyderabadi cuisine and biryani",
            "Rich handloom and textile traditions"
        ]
    },
        "chhattisgarh": {
        "name": "Chhattisgarh",
        "capital": "Raipur",
        "region": "central",
        "coordinates": {"lat": 21.2787, "lng": 81.8661},
        "description": "Chhattisgarh, known for its rich cultural heritage and natural beauty, is home to dense forests, waterfalls, and tribal communities. The state is famous for its ancient temples, wildlife sanctuaries, and vibrant festivals. Chhattisgarh's cuisine is diverse, with a variety of traditional dishes that reflect its agricultural roots.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Raipur", "Bastar", "Chitrakote Falls", "Kanger Valley National Park", "Sirpur",
            "Dongargarh", "Tirathgarh Falls", "Bhoramdeo Temple", "Nagarjunakonda", "Dudhadhari Monastery"
        ],
        "cuisine": [
            "Chana Samosa", "Farcha", "Bafauri", "Chhattisgarhi Thali", "Puran Poli",
            "Khurma", "Dubki Kadhi", "Rice", "Biryani", "Kheer"
        ],
        "culture": "Chhattisgarh's culture is a blend of tribal traditions and modern influences. The state is known for its folk dances, music, and festivals, particularly the Bastar Dussehra, which showcases its rich heritage.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. Summers can be extremely hot.",
        "transportation": "Raipur serves as the main transportation hub with an airport and railway station. The state has good road connectivity.",
        "highlights": [
            "Rich tribal culture and traditions",
            "Stunning waterfalls and natural beauty",
            "Ancient temples and archaeological sites",
            "Wildlife sanctuaries and national parks",
            "Vibrant festivals and local cuisine"
        ]
    },

    "goa": {
        "name": "Goa",
        "capital": "Panaji",
        "region": "west",
        "coordinates": {"lat": 15.2993, "lng": 74.1240},
        "description": "Goa, known for its stunning beaches, vibrant nightlife, and Portuguese heritage, is a popular tourist destination. The state offers a unique blend of relaxation and adventure, with water sports, beach parties, and cultural festivals. Goa's cuisine is a delightful mix of seafood and spices, reflecting its coastal culture.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Baga Beach", "Calangute Beach", "Old Goa", "Dudhsagar Waterfalls", "Anjuna Beach",
            "Fort Aguada", "Palolem Beach", "Basilica of Bom Jesus", "Spice Plantations", "Chapora Fort"
        ],
        "cuisine": [
            "Goan Fish Curry", "Prawn Balchão", "Vindaloo", "Xacuti", "Sannas",
            "Feni", "Pork Sorpotel", "Bebinca", "Rava Fried Fish", "Prawn Curry"
        ],
        "culture": "Goa's culture is a blend of Indian and Portuguese influences, evident in its architecture, music, and festivals. The state is famous for its vibrant carnival celebrations and traditional folk dances.",
        "bestTimeToVisit": "November to February is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Goa is well-connected by air, rail, and road. Dabolim Airport serves as the main airport, and the state has a good road network.",
        "highlights": [
            "Beautiful beaches and water sports",
            "Rich Portuguese heritage and architecture",
            "Vibrant nightlife and beach parties",
            "Delicious Goan cuisine",
            "Cultural festivals and events"
        ]
    },

    "madhya_pradesh": {
        "name": "Madhya Pradesh",
        "capital": "Bhopal",
        "region": "central",
        "coordinates": {"lat": 23.4734, "lng": 77.9470},
        "description": "Madhya Pradesh, known as the 'Heart of India,' is famous for its rich history, wildlife, and cultural heritage. The state is home to several UNESCO World Heritage Sites, including the Khajuraho temples and Sanchi Stupa. Madhya Pradesh offers diverse landscapes, from forests to plateaus, and is known for its vibrant festivals and traditional crafts.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Khajuraho", "Sanchi", "Bandhavgarh National Park", "Kanha National Park", "Ujjain",
            "Bhopal", "Orchha", "Pachmarhi", "Mandav", "Gwalior Fort"
        ],
        "cuisine": [
            "Dal Bafla", "Poha", "Bhutte ka Kees", "Chaat", "Biryani",
            "Kebabs", "Samosa", "Jalebi", "Lassi", "Kachori"
        ],
        "culture": "Madhya Pradesh's culture is a blend of various traditions, with a strong emphasis on music, dance, and festivals. The state celebrates various festivals, including Diwali, Holi, and the Khajuraho Dance Festival.",
        "bestTimeToVisit": "October to March is the best time to visit, as the weather is pleasant. Summers can be extremely hot.",
        "transportation": "Bhopal serves as the main transportation hub with an airport and railway station. The state has good road connectivity.",
        "highlights": [
            "UNESCO World Heritage Sites",
            "Rich wildlife and national parks",
            "Historical forts and palaces",
            "Vibrant festivals and local crafts",
            "Diverse cuisine and cultural experiences"
        ]
    },

    "maharashtra": {
        "name": "Maharashtra",
        "capital": "Mumbai",
        "region": "west",
        "coordinates": {"lat": 19.0760, "lng": 72.8777},
        "description": "Maharashtra, the wealthiest state in India, is known for its diverse culture, bustling cities, and beautiful landscapes. Mumbai, the capital, is the financial hub of India and is famous for its film industry, vibrant nightlife, and historical landmarks. The state offers a mix of urban and rural experiences, with hill stations, beaches, and cultural sites.",
        "image": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=800&auto=format&fit=crop",
        "touristPlaces": [
            "Mumbai", "Pune", "Aurangabad", "Nashik", "Lonavala",
            "Mahabaleshwar", "Ajanta Caves", "Ellora Caves", "Alibaug", "Kolhapur"
        ],
        "cuisine": [
            "Puran Poli", "Vada Pav", "Pav Bhaji", "Misal Pav", "Bhel Puri",
            "Bombay Sandwich", "Thalipeeth", "Modak", "Kothimbir Vadi", "Sol Kadhi"
        ],
        "culture": "Maharashtra's culture is a blend of various influences, with a strong emphasis on music, dance, and festivals. The state celebrates Ganesh Chaturthi with great enthusiasm, showcasing its vibrant traditions.",
        "bestTimeToVisit": "October to February is the best time to visit, as the weather is pleasant. The monsoon season (June-September) can bring heavy rains.",
        "transportation": "Mumbai serves as the main transportation hub with an international airport and extensive railway network. The state has good road connectivity.",
        "highlights": [
            "Vibrant city life in Mumbai",
            "Rich cultural heritage and festivals",
            "Historical sites and caves",
            "Beautiful hill stations and beaches",
            "Diverse cuisine and culinary experiences"
        ]
    }
}
# ---------------- Insert All States Data ----------------
def insert_all_states_data():
    client, db, collection = connect_to_mongodb()

    if collection is None:
        logger.error("Database connection failed. Cannot insert data.")
        return False, {"error": "Database connection failed"}

    try:
        success_count = 0
        error_count = 0
        results = []
        
        for state_key, state_data in indian_states_data.items():
            try:
                # Validate image URL
                image_url = state_data.get("image", "")
                image_valid = validate_image_url(image_url)
                
                if not image_valid:
                    logger.warning(f"Image URL for {state_data['name']} appears invalid: {image_url}")
                    # You could set a default image or handle this differently
                    # state_data["image"] = "https://default-image-url.com/placeholder.jpg"
                
                existing = collection.find_one({"name": state_data["name"]})

                state_result = {
                    "name": state_data["name"],
                    "image_url": image_url,
                    "image_valid": image_valid
                }

                if existing:
                    logger.info(f"{state_data['name']} exists. Updating data.")
                    result = collection.update_one(
                        {"name": state_data["name"]},
                        {"$set": state_data}
                    )
                    if result.modified_count > 0:
                        logger.info(f"{state_data['name']} data updated.")
                        state_result["status"] = "updated"
                        success_count += 1
                    else:
                        logger.info(f"No changes made to {state_data['name']}.")
                        state_result["status"] = "unchanged"
                        success_count += 1
                else:
                    logger.info(f"Inserting new {state_data['name']} data.")
                    result = collection.insert_one(state_data)
                    if result.inserted_id:
                        logger.info(f"{state_data['name']} inserted with ID: {result.inserted_id}")
                        state_result["status"] = "inserted"
                        state_result["id"] = str(result.inserted_id)
                        success_count += 1
                    else:
                        logger.error(f"Insertion failed for {state_data['name']}.")
                        state_result["status"] = "failed"
                        error_count += 1
                
                results.append(state_result)
                # Add a small delay to avoid overwhelming the server with requests
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing {state_data['name']}: {e}")
                results.append({
                    "name": state_data["name"],
                    "status": "error",
                    "error": str(e)
                })
                error_count += 1

        client.close()
        logger.info(f"Completed: {success_count} successful, {error_count} errors")
        
        return success_count > 0, {
            "total_states": len(indian_states_data),
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in inserting/updating state data: {e}")
        if client:
            client.close()
        return False, {"error": str(e)}

# ---------------- Routes ----------------
@app.route('/insert-all-states')
def insert_all_states_route():
    success, details = insert_all_states_data()
    if success:
        return jsonify({
            "status": "success",
            "message": "States data processing completed",
            "details": details
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to process all states data",
            "details": details
        }), 500

@app.route('/health')
def health_check():
    client, db, collection = connect_to_mongodb()

    if client is not None:
        client.close()
        return {
            "status": "healthy",
            "database": "connected",
            "message": "Service is running properly."
        }
    else:
        return {
            "status": "degraded",
            "database": "disconnected",
            "message": "Database connection failed."
        }, 503

# ---------------- Run ----------------
if __name__ == '__main__':
    # Insert all states when the server starts
    success, details = insert_all_states_data()
    if success:
        logger.info("Initial data insertion successful")
    else:
        logger.error("Initial data insertion failed")
    
    app.run(host='0.0.0.0', port=5000, debug=True)