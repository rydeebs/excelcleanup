import streamlit as st
import pandas as pd
import re
from io import BytesIO
import base64
from urllib.parse import urlparse
import time
import random

# Set page config
st.set_page_config(page_title="Data Cleanup and Enhancement Tool", layout="wide")

# Function to validate and correct email addresses
def validate_and_correct_email(email, country, website):
    if not email and not website:
        return ""
    
    # Extract username part (before @)
    username = ""
    if email:
        # If email contains @, get the part before it
        if "@" in email:
            username = email.split("@")[0].strip().lower()
        else:
            # If no @, assume the entire string is the username
            username = email.strip().lower()
    
    # If no username was found, return empty
    if not username:
        return ""
    
    # Get domain from website
    domain = ""
    if website:
        try:
            # Clean up the website URL
            website_url = website.strip()
            if not re.match(r'^https?://', website_url, re.I):
                website_url = 'https://' + website_url
            
            # Parse the URL and extract domain
            parsed_url = urlparse(website_url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix if present
            domain = re.sub(r'^www\.', '', domain)
        except Exception:
            # If website parsing fails, try basic extraction
            domain = website.strip().lower()
            domain = re.sub(r'^https?://', '', domain, flags=re.I)
            domain = re.sub(r'^www\.', '', domain, flags=re.I)
            domain = domain.split('/')[0]
    
    # If still no domain, try to extract from email
    if not domain and email and "@" in email and "." in email:
        domain = email.split("@")[1].strip().lower()
    
    # If still no domain, use default
    if not domain:
        domain = 'domain.com'
    
    # Construct the email
    return f"{username}@{domain}"

# Function to cleanup address
def cleanup_address(address_text):
    if not address_text:
        return ""
    
    # Common address patterns for various countries
    patterns = [
        # Street number followed by street name
        r'\b\d+\s+[A-Za-z\s]+\b(?:\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|court|ct|plaza|plz|square|sq|highway|hwy|route|rt))?',
        
        # Latin American address format (Calle, Carrera, Avenida, etc.)
        r'\b(?:Calle|Cl|Carrera|Cr|Cra|Avenida|Av|Autopista|Diagonal|Transversal|Trans)\s+\d+\s*[A-Za-z0-9\s#\-°\.]+',
        
        # Building number or unit number
        r'\b(?:Apt|Apartment|Unit|Suite|Ste|Building|Bldg|Floor|Fl|Room|Rm)\s+\d+[A-Za-z]?\b',
        
        # Hispanic style with # (e.g., "Calle 50 # 20-15")
        r'\b(?:Calle|Cl|Carrera|Cr|Cra|Avenida|Av)\s+\d+\s*#\s*\d+(?:\s*-\s*\d+)?',
        
        # Hispanic styles for other countries
        r'\b(?:Paseo|Rua|Avenida|Av|Calle|Cl|Carrer|Jalan|Jln|Via|Viale|Estrada|Ruta)\s+[A-Za-z0-9\s#\-°\.]+',
        
        # Asian address styles
        r'\b\d+\s+(?:Jalan|Jln|Soi)\s+[A-Za-z0-9\s]+',
        
        # Middle Eastern address styles
        r'\b(?:Al|El)\s+[A-Za-z]+\s+(?:Street|Road|Avenue)',
        
        # PO Box
        r'\bP\.?O\.?\s*Box\s+\d+\b',
        
        # Generic number + word pattern (might catch some addresses)
        r'\b\d+\s+[A-Za-z]{3,}\b'
    ]
    
    # Try to find address patterns in the text
    for pattern in patterns:
        match = re.search(pattern, address_text, re.I)
        if match:
            # Found a potential address
            return match.group(0).strip()
    
    # If no patterns matched, look for any segment with numbers and letters that might be an address
    segments = re.split(r'[,;\n]+', address_text)
    
    for segment in segments:
        # Look for segments that have both numbers and letters (typical for addresses)
        if re.search(r'\d', segment) and re.search(r'[A-Za-z]', segment) and len(segment) > 5:
            return segment.strip().replace(r'\s+', ' ')
    
    # If still nothing found, return the first part of the text (limited to 50 chars)
    first_part = address_text.strip().split(r'[,;\n]')[0]
    if len(first_part) > 50:
        first_part = first_part[:50]
    return re.sub(r'\s+', ' ', first_part)

# Function to extract city from address
def extract_city(address_text, country):
    if not address_text:
        return ""
    
    # Dictionary of major cities by country (expanded for Central/South America and FTA countries)
    cities_by_country = {
        'Colombia': ['Bogota', 'Medellin', 'Cali', 'Barranquilla', 'Cartagena', 'Cucuta', 'Bucaramanga', 
                     'Pereira', 'Santa Marta', 'Manizales', 'Ibague', 'Pasto', 'Neiva', 'Villavicencio', 
                     'Armenia', 'Valledupar', 'Monteria', 'Sincelejo', 'Popayan', 'Palmira', 'Buenaventura', 
                     'Floridablanca', 'Barrancabermeja', 'Tunja', 'Tulua'],
        
        'Mexico': ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana', 'Leon', 'Juarez', 
                   'Merida', 'Chihuahua', 'Cancun', 'Queretaro', 'San Luis Potosi', 'Hermosillo', 
                   'Aguascalientes', 'Morelia', 'Veracruz', 'Mexicali', 'Culiacan', 'Acapulco', 
                   'Tampico', 'Cuernavaca', 'Toluca', 'Torreon', 'Durango', 'Oaxaca'],
        
        'Brazil': ['Sao Paulo', 'Rio de Janeiro', 'Brasilia', 'Salvador', 'Fortaleza', 'Belo Horizonte', 
                   'Manaus', 'Curitiba', 'Recife', 'Porto Alegre', 'Belem', 'Goiania', 'Guarulhos', 
                   'Campinas', 'Sao Luis', 'Maceio', 'Duque de Caxias', 'Natal', 'Campo Grande', 
                   'Teresina', 'Sao Bernardo do Campo', 'Nova Iguacu', 'Joao Pessoa', 'Santo Andre', 
                   'Osasco', 'Ribeirao Preto', 'Jaboatao dos Guararapes', 'Uberlandia'],
        
        'Chile': ['Santiago', 'Valparaiso', 'Concepcion', 'La Serena', 'Antofagasta', 'Temuco', 
                  'Rancagua', 'Talca', 'Arica', 'Iquique', 'Puerto Montt', 'Coquimbo', 'Osorno', 
                  'Quillota', 'Calama', 'Chillan', 'Valdivia', 'Punta Arenas', 'Copiapo', 'Curico', 
                  'Los Angeles', 'Melipilla', 'San Antonio', 'Linares', 'Ovalle'],
        
        'Argentina': ['Buenos Aires', 'Cordoba', 'Rosario', 'Mendoza', 'San Miguel de Tucuman', 
                     'La Plata', 'Mar del Plata', 'Salta', 'Santa Fe', 'San Juan', 'Resistencia', 
                     'Santiago del Estero', 'Corrientes', 'Posadas', 'San Salvador de Jujuy', 
                     'Bahia Blanca', 'Parana', 'Neuquen', 'Formosa', 'La Rioja', 'Rio Cuarto', 
                     'Comodoro Rivadavia', 'San Luis', 'Tandil', 'San Rafael'],
        
        'Peru': ['Lima', 'Arequipa', 'Trujillo', 'Chiclayo', 'Piura', 'Iquitos', 'Cusco', 'Huancayo', 
                 'Tacna', 'Juliaca', 'Ica', 'Pucallpa', 'Chimbote', 'Sullana', 'Ayacucho', 'Chincha Alta', 
                 'Huanuco', 'Cajamarca', 'Puno', 'Tumbes', 'Tarapoto', 'Huacho', 'Huaraz', 'Pisco', 'Moyobamba'],
        
        'Ecuador': ['Quito', 'Guayaquil', 'Cuenca', 'Santo Domingo', 'Machala', 'Duran', 'Manta', 
                   'Portoviejo', 'Loja', 'Ambato', 'Esmeraldas', 'Quevedo', 'Riobamba', 'Milagro', 
                   'Ibarra', 'Babahoyo', 'Sangolqui', 'Santa Elena', 'La Libertad', 'Latacunga'],
        
        'Venezuela': ['Caracas', 'Maracaibo', 'Valencia', 'Barquisimeto', 'Maracay', 'Ciudad Guayana', 
                     'Barcelona', 'Maturin', 'Puerto La Cruz', 'Petare', 'Turmero', 'Baruta', 'Barinas', 
                     'Mérida', 'Cumana', 'Cabimas', 'San Cristobal', 'Ciudad Bolivar', 'Guatire', 
                     'Punto Fijo', 'Acarigua', 'Carupano', 'Los Teques', 'Coro', 'El Tigre'],
        
        'Uruguay': ['Montevideo', 'Salto', 'Ciudad de la Costa', 'Paysandu', 'Las Piedras', 'Rivera', 
                   'Maldonado', 'Tacuarembo', 'Melo', 'Mercedes', 'Artigas', 'Minas', 'San Jose de Mayo', 
                   'Durazno', 'Florida', 'Treinta y Tres', 'Rocha', 'Fray Bentos', 'Trinidad', 'Colonia del Sacramento'],
        
        'Paraguay': ['Asuncion', 'Ciudad del Este', 'San Lorenzo', 'Luque', 'Capiata', 'Lambare', 
                    'Fernando de la Mora', 'Limpio', 'Nemby', 'Encarnacion', 'Mariano Roque Alonso', 
                    'Pedro Juan Caballero', 'Villa Elisa', 'Ita', 'Villarrica', 'Caaguazu', 'Coronel Oviedo', 
                    'Concepcion', 'Presidente Franco', 'Pilar'],
        
        'Bolivia': ['La Paz', 'Santa Cruz de la Sierra', 'Cochabamba', 'El Alto', 'Oruro', 'Sucre', 
                   'Tarija', 'Potosi', 'Sacaba', 'Montero', 'Trinidad', 'Quillacollo', 'Riberalta', 
                   'Warnes', 'Yacuiba', 'Camiri', 'Tupiza', 'Villa Montes', 'Villazon', 'Guayaramerin'],
        
        'Costa Rica': ['San Jose', 'Alajuela', 'Cartago', 'Heredia', 'Liberia', 'Puntarenas', 'Limon', 
                      'Perez Zeledon', 'Santa Cruz', 'Nicoya', 'Turrialba', 'Ciudad Quesada', 'Siquirres', 
                      'Canas', 'Grecia', 'Guapiles', 'San Isidro', 'Atenas', 'Esparza', 'Puriscal'],
        
        'Panama': ['Panama City', 'San Miguelito', 'Juan Diaz', 'David', 'Arraijan', 'Colon', 'La Chorrera', 
                  'Santiago', 'Chitre', 'Penonome', 'Bocas del Toro', 'Aguadulce', 'Changuinola', 'La Concepcion', 
                  'Las Tablas', 'Puerto Armuelles', 'Boquete', 'El Porvenir', 'Los Santos', 'Rio Abajo'],
        
        'Guatemala': ['Guatemala City', 'Mixco', 'Villa Nueva', 'Quetzaltenango', 'Escuintla', 'Chinautla', 
                     'Villa Canales', 'San Juan Sacatepequez', 'Chimaltenango', 'Coban', 'Huehuetenango', 
                     'Mazatenango', 'Retalhuleu', 'Totonicapan', 'Jalapa', 'Puerto Barrios', 'Antigua Guatemala', 
                     'Santa Lucia Cotzumalguapa', 'Solola', 'San Pedro Sacatepequez'],
        
        'El Salvador': ['San Salvador', 'Santa Ana', 'Soyapango', 'San Miguel', 'Mejicanos', 'Santa Tecla', 
                       'Apopa', 'Delgado', 'Ahuachapan', 'Ilopango', 'Zacatecoluca', 'Cojutepeque', 'Usulutan', 
                       'San Vicente', 'San Marcos', 'Chalatenango', 'La Union', 'Sensuntepeque', 'Metapan', 'Acajutla'],
        
        'Honduras': ['Tegucigalpa', 'San Pedro Sula', 'La Ceiba', 'Choloma', 'El Progreso', 'Choluteca', 
                    'Comayagua', 'Puerto Cortes', 'Danli', 'Juticalpa', 'Siguatepeque', 'Santa Rosa de Copan', 
                    'Tela', 'Villanueva', 'Potrerillos', 'La Lima', 'La Paz', 'Olanchito', 'Nacaome', 'Santa Barbara'],
        
        'Nicaragua': ['Managua', 'Leon', 'Masaya', 'Tipitapa', 'Chinandega', 'Matagalpa', 'Esteli', 'Granada', 
                     'Ciudad Sandino', 'Juigalpa', 'Jinotega', 'El Viejo', 'Nueva Guinea', 'Diriamba', 'Chichigalpa', 
                     'Rivas', 'Jalapa', 'Jinotepe', 'Ocotal', 'Somoto'],
        
        'Dominican Republic': ['Santo Domingo', 'Santiago de los Caballeros', 'Los Alcarrizos', 'Santo Domingo Este', 
                             'Santo Domingo Norte', 'Santo Domingo Oeste', 'San Pedro de Macoris', 'La Romana', 
                             'San Francisco de Macoris', 'San Cristobal', 'Puerto Plata', 'La Vega', 'Moca', 
                             'Bani', 'Bonao', 'Higuey', 'Barahona', 'Cotui', 'Nagua', 'Azua'],
        
        'Jamaica': ['Kingston', 'Montego Bay', 'Portmore', 'Spanish Town', 'Mandeville', 'May Pen', 'Old Harbour', 
                   'Savanna-la-Mar', 'Port Antonio', 'St. Anns Bay', 'Linstead', 'Black River', 'Ocho Rios', 
                   'Falmouth', 'Lucea', 'Negril', 'Morant Bay', 'Chapelton', 'Port Maria', 'Yallahs'],
        
        'Trinidad and Tobago': ['Port of Spain', 'San Fernando', 'Chaguanas', 'Mon Repos', 'Arima', 'Tunapuna', 
                               'Sangre Grande', 'Point Fortin', 'Couva', 'Siparia', 'Rio Claro', 'Scarborough', 
                               'Penal', 'Gasparillo', 'Princess Town', 'San Juan', 'Diego Martin', 'Fyzabad', 
                               'Arouca', 'Valencia'],
        
        'Canada': ['Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Edmonton', 'Ottawa', 'Winnipeg', 
                  'Quebec City', 'Hamilton', 'Kitchener', 'London', 'Victoria', 'Halifax', 'Oshawa', 
                  'Windsor', 'Saskatoon', 'Regina', 'St. Catharines', 'Sherbrooke', 'Barrie', 'Kelowna', 
                  'Kingston', 'Abbotsford', 'Trois-Rivieres', 'Saint John'],
        
        'Australia': ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Gold Coast', 'Canberra', 
                     'Newcastle', 'Wollongong', 'Logan City', 'Geelong', 'Hobart', 'Townsville', 'Cairns', 
                     'Darwin', 'Toowoomba', 'Ballarat', 'Bendigo', 'Launceston', 'Mackay', 'Rockhampton', 
                     'Bundaberg', 'Bunbury', 'Hervey Bay', 'Wagga Wagga'],
        
        'New Zealand': ['Auckland', 'Wellington', 'Christchurch', 'Hamilton', 'Tauranga', 'Napier-Hastings', 
                       'Dunedin', 'Palmerston North', 'Nelson', 'Rotorua', 'New Plymouth', 'Whangarei', 
                       'Invercargill', 'Whanganui', 'Gisborne', 'Blenheim', 'Pukekohe', 'Timaru', 
                       'Taupo', 'Masterton'],
                       
        'Singapore': ['Singapore'],
        
        'South Korea': ['Seoul', 'Busan', 'Incheon', 'Daegu', 'Daejeon', 'Gwangju', 'Suwon', 'Ulsan', 
                      'Seongnam', 'Goyang', 'Bucheon', 'Ansan', 'Anyang', 'Changwon', 'Jeonju', 
                      'Cheongju', 'Pohang', 'Uijeongbu', 'Hwaseong', 'Yongin'],
        
        'Japan': ['Tokyo', 'Yokohama', 'Osaka', 'Nagoya', 'Sapporo', 'Kobe', 'Kyoto', 'Fukuoka', 
                 'Kawasaki', 'Saitama', 'Hiroshima', 'Sendai', 'Kitakyushu', 'Chiba', 'Sakai', 
                 'Kumamoto', 'Niigata', 'Okayama', 'Hamamatsu', 'Sagamihara'],
        
        'Israel': ['Jerusalem', 'Tel Aviv', 'Haifa', 'Rishon LeZion', 'Petah Tikva', 'Ashdod', 'Netanya', 
                  'Beer Sheva', 'Holon', 'Bnei Brak', 'Ramat Gan', 'Rehovot', 'Herzliya', 'Kfar Saba', 
                  'Modiin', 'Ashkelon', 'Bat Yam', 'Nahariya', 'Lod', 'Nazareth'],
        
        'South Africa': ['Johannesburg', 'Cape Town', 'Durban', 'Pretoria', 'Port Elizabeth', 'Bloemfontein', 
                        'Nelspruit', 'Kimberley', 'Polokwane', 'Pietermaritzburg', 'East London', 'Rustenburg', 
                        'Vereeniging', 'Potchefstroom', 'Welkom', 'Newcastle', 'Krugersdorp', 'Witbank', 
                        'Centurion', 'Stellenbosch'],
        
        'Morocco': ['Casablanca', 'Rabat', 'Fes', 'Marrakech', 'Agadir', 'Tangier', 'Meknes', 'Oujda', 
                   'Kenitra', 'Tetouan', 'Safi', 'Mohammedia', 'El Jadida', 'Taza', 'Beni Mellal', 
                   'Nador', 'Settat', 'Berrechid', 'Khouribga', 'Larache'],
        
        'Egypt': ['Cairo', 'Alexandria', 'Giza', 'Shubra El-Kheima', 'Port Said', 'Suez', 'Luxor', 
                 'Aswan', 'Ismailia', 'Faiyum', 'Zagazig', 'Damietta', 'Asyut', 'Tanta', 'Sohag', 
                 'Mansoura', 'Hurghada', 'Beni Suef', 'Minya', 'Qena'],
        
        'Turkey': ['Istanbul', 'Ankara', 'Izmir', 'Bursa', 'Adana', 'Gaziantep', 'Konya', 'Antalya', 
                  'Mersin', 'Diyarbakir', 'Kayseri', 'Eskisehir', 'Samsun', 'Denizli', 'Kahramanmaras', 
                  'Ordu', 'Erzurum', 'Malatya', 'Trabzon', 'Elazig'],
        
        'United Arab Emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Al Ain', 'Ajman', 'Ras Al-Khaimah', 
                               'Fujairah', 'Umm Al-Quwain'],
        
        'Saudi Arabia': ['Riyadh', 'Jeddah', 'Mecca', 'Medina', 'Dammam', 'Taif', 'Tabuk', 'Buraidah', 
                       'Khamis Mushait', 'Abha', 'Najran', 'Yanbu', 'Khobar', 'Sakaka', 'Al Bahah', 
                       'Jubail', 'Jizan', 'Hafar Al-Batin', 'Dhahran', 'Qatif'],
        
        'Qatar': ['Doha', 'Al Rayyan', 'Al Wakrah', 'Al Khor', 'Mesaieed', 'Dukhan', 'Al Shamal', 
                 'Madinat ash Shamal', 'Umm Salal Muhammad', 'Al Wukair'],
        
        'Kuwait': ['Kuwait City', 'Hawalli', 'Salmiya', 'Al Ahmadi', 'Sabah Al-Salem', 'Al Farwaniyah', 
                  'Al Jahra', 'Mangaf', 'Fahaheel', 'Ar Rumaithiya'],
        
        'Bahrain': ['Manama', 'Riffa', 'Muharraq', 'Hamad Town', 'A\'Ali', 'Isa Town', 'Sitra', 
                   'Budaiya', 'Jidhafs', 'Sanabis'],
        
        'Oman': ['Muscat', 'Seeb', 'Salalah', 'Sohar', 'Nizwa', 'Sur', 'Ibri', 'Saham', 'Barka', 'Rustaq'],
        
        'Jordan': ['Amman', 'Zarqa', 'Irbid', 'Russeifa', 'Aqaba', 'Madaba', 'Mafraq', 'Jerash', 
                  'Salt', 'Karak', 'Tafilah', 'Ma\'an', 'Ajloun', 'Ramtha'],
        
        'United Kingdom': ['London', 'Birmingham', 'Manchester', 'Glasgow', 'Liverpool', 'Bristol', 'Sheffield', 
                          'Leeds', 'Edinburgh', 'Leicester', 'Coventry', 'Bradford', 'Belfast', 'Nottingham', 
                          'Kingston upon Hull', 'Newcastle upon Tyne', 'Southampton', 'Reading', 'Derby', 'Aberdeen']
    }
    
    # Create a regex of cities for the given country (case insensitive)
    if country and country in cities_by_country:
        city_list = cities_by_country[country]
        city_pattern = r'\b(' + '|'.join(city_list) + r')\b'
        
        # First look for cities from our dictionary
        match = re.search(city_pattern, address_text, re.I)
        if match:
            return match.group(0).strip()
    
    # If no match with known cities, try pattern matching
    
    # Special case for "Medellin - Colombia" pattern as in the example
    special_pattern = r'\b([A-Z][a-zA-Z]+)\s*-\s*[A-Za-z]+\b'
    special_match = re.search(special_pattern, address_text, re.I)
    if special_match:
        return special_match.group(1).strip()
    
    # Split by common delimiters and look for capitalized words that might be cities
    parts = re.split(r'[\s,;:\-\/]+', address_text)
    candidates = []
    
    for part in parts:
        # Skip empty or very short parts
        if not part or len(part) < 3:
            continue
        
        # Check if it's capitalized and not a street type or direction
        if (part and part[0].isupper() and
            not re.match(r'^(St|Ave|Rd|Blvd|Ln|Dr|Ct|Plz|Sq|Hwy|Rt|North|South|East|West|NE|NW|SE|SW)$', part, re.I) and
            not re.match(r'^\d+$', part)):  # Not just numbers
            candidates.append(part)
    
    # Return the best candidate (preferring longer words, as they're more likely to be city names)
    if candidates:
        candidates.sort(key=len, reverse=True)
        return candidates[0]
    
    return ""

# Function to extract logo from website
def extract_logo_from_website(website):
    if not website:
        return ""
    
    try:
        # Clean up the website URL to get just the domain
        domain = website.strip().lower()
        domain = re.sub(r'^https?://', '', domain, flags=re.I)
        domain = re.sub(r'^www\.', '', domain, flags=re.I)
        domain = domain.split('/')[0]
        
        # Use Clearbit's logo API
        return f"https://logo.clearbit.com/{domain}"
    
    except Exception as e:
        st.error(f"Error extracting logo: {str(e)}")
        return f"https://via.placeholder.com/150?text=Error"

# Function to validate and correct geographic coordinates based on country
def validate_coordinates(latitude, longitude, country):
    # Dictionary of country bounding boxes (approximate min/max lat/lon)
    # Format: [min_lat, max_lat, min_lon, max_lon]
    country_bounds = {
        'Colombia': [1.0, 12.5, -79.0, -67.0],
        'Mexico': [14.5, 32.7, -118.4, -86.7],
        'Brazil': [-33.8, 5.3, -73.9, -34.8],
        'Chile': [-55.9, -17.5, -80.0, -66.0],
        'Argentina': [-55.0, -21.8, -73.6, -53.6],
        'Peru': [-18.4, -0.0, -81.4, -68.7],
        'Ecuador': [-5.0, 1.8, -81.0, -75.0],
        'Venezuela': [0.6, 12.2, -73.4, -59.8],
        'Canada': [42.0, 83.0, -141.0, -52.0],
        'United States': [24.5, 49.5, -125.0, -66.0],
        'United Kingdom': [49.9, 59.5, -8.6, 1.8],
        'Australia': [-43.6, -10.6, 113.1, 153.6],
        'Japan': [30.4, 45.5, 130.9, 145.8],
        'South Korea': [33.1, 38.6, 125.9, 129.6],
        'China': [18.2, 53.6, 73.5, 134.8],
        'India': [6.7, 35.5, 68.1, 97.4],
        'South Africa': [-34.8, -22.1, 16.5, 32.9],
        'Egypt': [22.0, 31.7, 24.7, 36.9],
        'Morocco': [27.7, 35.9, -13.2, -1.0],
        'Saudi Arabia': [16.3, 32.2, 34.5, 55.7],
        'United Arab Emirates': [22.6, 26.1, 51.5, 56.4],
        'Turkey': [35.8, 42.1, 26.0, 44.8],
        'Germany': [47.3, 55.1, 5.9, 15.0],
        'France': [41.3, 51.1, -5.1, 9.6],
        'Italy': [36.6, 47.1, 6.6, 18.5],
        'Spain': [36.0, 43.8, -9.4, 3.4],
        'Netherlands': [50.8, 53.5, 3.3, 7.2],
        'Russia': [41.2, 81.9, 19.6, 180.0],
        'Costa Rica': [8.0, 11.2, -85.9, -82.5],
        'Panama': [7.2, 9.6, -83.0, -77.2],
        'Guatemala': [13.7, 17.8, -92.2, -88.2],
        'El Salvador': [13.2, 14.5, -90.1, -87.7],
        'Honduras': [12.9, 16.5, -89.4, -83.1],
        'Nicaragua': [10.7, 15.0, -87.7, -83.1],
        'Dominican Republic': [17.5, 19.9, -72.0, -68.3],
        'Jamaica': [17.7, 18.5, -78.4, -76.2],
        'Trinidad and Tobago': [10.0, 11.4, -61.9, -60.5]
    }
    
    try:
        # Parse coordinates to float
        lat = float(latitude) if isinstance(latitude, str) else latitude
        lon = float(longitude) if isinstance(longitude, str) else longitude
        
        # Check if the country exists in our database
        if country not in country_bounds:
            # If country not in database, return the original coordinates
            return lat, lon
        
        bounds = country_bounds[country]
        min_lat, max_lat, min_lon, max_lon = bounds
        
        # Check if coordinates are within country bounds
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            # Coordinates are already valid
            return lat, lon
        else:
            # Generate valid coordinates within the country bounds
            valid_lat = min_lat + (max_lat - min_lat) * random.random()
            valid_lon = min_lon + (max_lon - min_lon) * random.random()
            
            # Round to 6 decimal places
            valid_lat = round(valid_lat, 6)
            valid_lon = round(valid_lon, 6)
            
            return valid_lat, valid_lon
    
    except (ValueError, TypeError):
        # If coordinates are invalid or can't be parsed, generate random ones for the country
        if country in country_bounds:
            bounds = country_bounds[country]
            min_lat, max_lat, min_lon, max_lon = bounds
            
            valid_lat = min_lat + (max_lat - min_lat) * random.random()
            valid_lon = min_lon + (max_lon - min_lon) * random.random()
            
            # Round to 6 decimal places
            valid_lat = round(valid_lat, 6)
            valid_lon = round(valid_lon, 6)
            
            return valid_lat, valid_lon
        else:
            # Default fallback if country is unknown
            return 0.0, 0.0

# Main app layout
st.title("Data Cleanup and Enhancement Tool")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["1. Upload File", "2. Configure Columns", "3. Process Data", "4. Results & Export"])

# Store state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'column_mappings' not in st.session_state:
    st.session_state.column_mappings = {
        'email': '',
        'website': '',
        'address': '',
        'city': '',
        'country': '',
        'logo': '',
        'latitude': '',
        'longitude': ''
    }

# File Upload Tab
with tab1:
    st.header("Upload Your File")
    st.write("Supported formats: CSV, Excel (.xlsx, .xls)")
    
    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            # Determine file type and read accordingly
            if uploaded_file.name.endswith('.csv'):
                data = pd.read_csv(uploaded_file)
            else:  # Excel file
                data = pd.read_excel(uploaded_file)
            
            st.session_state.data = data
            
            st.success(f"File '{uploaded_file.name}' uploaded successfully!")
            st.write(f"Found {len(data.columns)} columns and {len(data)} rows.")
            
            # Preview the data
            st.subheader("Data Preview")
            st.dataframe(data.head())
            
            st.info("You can now proceed to the 'Configure Columns' tab")
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# Configure Columns Tab
with tab2:
    if st.session_state.data is not None:
        st.header("Configure Column Mappings")
        st.write("Select which columns in your data correspond to each field:")
        
        # Create two columns for the form layout
        col1, col2 = st.columns(2)
        
        # Column selectors
        with col1:
            st.session_state.column_mappings['email'] = st.selectbox(
                "Email Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['email'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['email'])
            )
            
            st.session_state.column_mappings['address'] = st.selectbox(
                "Address Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['address'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['address'])
            )
            
            st.session_state.column_mappings['country'] = st.selectbox(
                "Country Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['country'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['country'])
            )
            
            st.session_state.column_mappings['latitude'] = st.selectbox(
                "Latitude Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['latitude'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['latitude'])
            )
        
        with col2:
            st.session_state.column_mappings['website'] = st.selectbox(
                "Website Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['website'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['website'])
            )
            
            st.session_state.column_mappings['city'] = st.selectbox(
                "City Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['city'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['city'])
            )
            
            st.session_state.column_mappings['logo'] = st.selectbox(
                "Logo Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['logo'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['logo'])
            )
            
            st.session_state.column_mappings['longitude'] = st.selectbox(
                "Longitude Column:",
                options=[''] + list(st.session_state.data.columns),
                index=0 if not st.session_state.column_mappings['longitude'] else 
                      list([''] + list(st.session_state.data.columns)).index(st.session_state.column_mappings['longitude'])
            )
        
        st.info("After selecting your columns, proceed to the 'Process Data' tab")
        
    else:
        st.info("Please upload a file in the previous step.")

# Process Data Tab
with tab3:
    if st.session_state.data is not None:
        st.header("Process Data")
        
        # Show selected configuration
        st.subheader("Selected Configuration:")
        config_text = ""
        for field, column in st.session_state.column_mappings.items():
            if column:
                config_text += f"- {field.capitalize()}: {column}\n"
        
        if config_text:
            st.markdown(config_text)
        else:
            st.warning("No columns have been configured.")
        
        # Show processing tasks
        st.subheader("Processing Tasks:")
        tasks_text = ""
        if st.session_state.column_mappings['email'] and st.session_state.column_mappings['website']:
            tasks_text += f"- Validate and correct email addresses in column \"{st.session_state.column_mappings['email']}\"\n"
        
        if st.session_state.column_mappings['address']:
            tasks_text += f"- Clean up addresses in column \"{st.session_state.column_mappings['address']}\"\n"
        
        if st.session_state.column_mappings['city'] and st.session_state.column_mappings['address'] and st.session_state.column_mappings['country']:
            tasks_text += f"- Extract cities from addresses and update column \"{st.session_state.column_mappings['city']}\"\n"
        
        if st.session_state.column_mappings['logo'] and st.session_state.column_mappings['website']:
            tasks_text += f"- Extract company logos from websites and update column \"{st.session_state.column_mappings['logo']}\"\n"
            
        if st.session_state.column_mappings['latitude'] and st.session_state.column_mappings['longitude'] and st.session_state.column_mappings['country']:
            tasks_text += f"- Validate and correct geographic coordinates for column \"{st.session_state.column_mappings['latitude']}\" and \"{st.session_state.column_mappings['longitude']}\"\n"
        
        if tasks_text:
            st.markdown(tasks_text)
        else:
            st.warning("No tasks to perform based on current configuration.")
        
        # Process data button
        if st.button("Process Data Now"):
            if not any(st.session_state.column_mappings.values()):
                st.error("Please configure at least one column mapping before processing.")
            else:
                # Create a copy of the data for processing
                processed_data = st.session_state.data.copy()
                
                # Set up progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process the data
                total_rows = len(processed_data)
                
                for i, (idx, row) in enumerate(processed_data.iterrows()):
                    # Update progress
                    progress = (i + 1) / total_rows
                    progress_bar.progress(progress)
                    status_text.text(f"Processing row {i+1} of {total_rows}...")
                    
                    # Process email if column selected
                    email_col = st.session_state.column_mappings['email']
                    website_col = st.session_state.column_mappings['website']
                    country_col = st.session_state.column_mappings['country']
                    
                    if email_col and website_col:
                        email_value = str(row[email_col]) if pd.notna(row[email_col]) else ""
                        website_value = str(row[website_col]) if pd.notna(row[website_col]) else ""
                        country_value = str(row[country_col]) if country_col and pd.notna(row[country_col]) else ""
                        
                        processed_data.at[idx, email_col] = validate_and_correct_email(
                            email_value, country_value, website_value
                        )
                    
                    # Clean up address if column selected
                    address_col = st.session_state.column_mappings['address']
                    if address_col:
                        address_value = str(row[address_col]) if pd.notna(row[address_col]) else ""
                        processed_data.at[idx, address_col] = cleanup_address(address_value)
                    
                    # Extract city if columns selected
                    city_col = st.session_state.column_mappings['city']
                    if city_col and address_col and country_col:
                        address_value = str(row[address_col]) if pd.notna(row[address_col]) else ""
                        country_value = str(row[country_col]) if pd.notna(row[country_col]) else ""
                        processed_data.at[idx, city_col] = extract_city(address_value, country_value)
                    
                    # Extract logo if columns selected
                    logo_col = st.session_state.column_mappings['logo']
                    if logo_col and website_col:
                        website_value = str(row[website_col]) if pd.notna(row[website_col]) else ""
                        processed_data.at[idx, logo_col] = extract_logo_from_website(website_value)
                    
                    # Validate and correct coordinates if columns selected
                    lat_col = st.session_state.column_mappings['latitude']
                    lon_col = st.session_state.column_mappings['longitude']
                    if lat_col and lon_col and country_col:
                        lat_value = row[lat_col] if pd.notna(row[lat_col]) else 0
                        lon_value = row[lon_col] if pd.notna(row[lon_col]) else 0
                        country_value = str(row[country_col]) if pd.notna(row[country_col]) else ""
                        
                        valid_lat, valid_lon = validate_coordinates(lat_value, lon_value, country_value)
                        processed_data.at[idx, lat_col] = valid_lat
                        processed_data.at[idx, lon_col] = valid_lon
                    
                    # Small delay to make progress visible
                    time.sleep(0.01)
                
                # Update session state with processed data
                st.session_state.processed_data = processed_data
                
                # Complete progress bar
                progress_bar.progress(1.0)
                status_text.text("Processing complete!")
                
                # Success message
                st.success("Data processing completed successfully! Go to the Results tab to view and export your data.")
    
    else:
        st.info("Please upload a file and configure columns in the previous steps.")

# Results & Export Tab
with tab4:
    if st.session_state.processed_data is not None:
        st.header("Results & Export")
        
        # Display the processed data
        st.subheader("Processed Data Preview")
        st.dataframe(st.session_state.processed_data.head(10))
        
        if len(st.session_state.processed_data) > 10:
            st.info(f"Showing 10 of {len(st.session_state.processed_data)} rows. Export to view all data.")
        
        # Export options
        st.subheader("Export Options")
        
        col_csv, col_excel = st.columns(2)
        
        with col_csv:
            # Create a download button for CSV
