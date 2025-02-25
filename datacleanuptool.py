import streamlit as st
import pandas as pd
import re
import requests
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
    
    # If still no domain, use country TLD or default
    if not domain:
        country_tlds = {
            'Chile': 'domain.cl',
            'Brazil': 'domain.br',
            'Argentina': 'domain.ar',
            'Colombia': 'domain.co',
            'Mexico': 'domain.mx',
            'Peru': 'domain.pe',
            'Ecuador': 'domain.ec',
            'Venezuela': 'domain.ve',
            'Uruguay': 'domain.uy',
            'Paraguay': 'domain.py',
            'Bolivia': 'domain.bo',
            'Costa Rica': 'domain.cr',
            'Panama': 'domain.pa',
            'Guatemala': 'domain.gt',
            'El Salvador': 'domain.sv',
            'Honduras': 'domain.hn',
            'Nicaragua': 'domain.ni',
            'Dominican Republic': 'domain.do',
            'Jamaica': 'domain.jm',
            'Trinidad and Tobago': 'domain.tt',
            'Canada': 'domain.ca',
            'United Kingdom': 'domain.uk',
            'Australia': 'domain.au',
            'New Zealand': 'domain.nz',
            'Singapore': 'domain.sg',
            'South Korea': 'domain.kr',
            'Japan': 'domain.jp',
            'Israel': 'domain.il',
            'South Africa': 'domain.za',
            'Morocco': 'domain.ma',
            'Egypt': 'domain.eg',
            'Turkey': 'domain.tr',
            'United Arab Emirates': 'domain.ae',
            'Saudi Arabia': 'domain.sa',
            'Qatar': 'domain.qa',
            'Kuwait': 'domain.kw',
            'Bahrain': 'domain.bh',
            'Oman': 'domain.om',
            'Jordan': 'domain.jo',
        }
        
        domain = country_tlds.get(country, 'domain.com') if country else 'domain.com'
    
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
    
    # If no match with known cities, try some heuristics
    
    # Look for patterns like "City: X" or "X, City" or "City of X"
    city_indicator_patterns = [
        r'\bCity:\s*([A-Z][a-zA-Z\s]+)(?=[\s,;]|$)',
        r'\b([A-Z][a-zA-Z\s]+),\s*(?:City|Town|Village|Municipality)(?=[\s,;]|$)',
        r'\b(?:City|Town|Village|Municipality)\s+of\s+([A-Z][a-zA-Z\s]+)(?=[\s,;]|$)',
        r'\b([A-Z][a-zA-Z\s]+)(?=\s*-\s*(?:Colombia|Mexico|Brazil|Chile|Argentina|Peru|Ecuador|Venezuela|Uruguay|Paraguay|Bolivia|Panama|Guatemala|El Salvador|Honduras|Nicaragua|Dominican Republic|Jamaica|Trinidad|Canada|Australia|New Zealand|Singapore|South Korea|Japan|Israel|South Africa|Morocco|Egypt|Turkey|UAE|Saudi Arabia|Qatar|Kuwait|Bahrain|Oman|Jordan|UK))(?=[\s,;]|$)'
    ]
    
    for pattern in city_indicator_patterns:
        match = re.search(pattern, address_text, re.I)
        if match:
            return match[1].strip()
    
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
        if (part[0].isupper() and
            not re.match(r'^(St|Ave|Rd|Blvd|Ln|Dr|Ct|Plz|Sq|Hwy|Rt|North|South|East|West|NE|NW|SE|SW)$', part, re.I) and
            not re.match(r'^\d+$', part)):  # Not just numbers
            candidates.append(part)
    
    # Return the best candidate (preferring longer words, as they're more likely to be city names)
    if candidates:
        candidates.sort(key=len, reverse=True)
        return candidates[0]
    
    return ""

# Function to extract logo from website using Clearbit API
def extract_logo_from_website(website):
    if not website:
        return ""
    
    try:
        # Clean up the website URL to get just the domain
        domain = website.strip().lower()
        domain = re.sub(r'^https?://', '', domain, flags=re.I)
        domain = re.sub(r'^www\.', '', domain, flags=re.I)
        domain = domain.split('/')[0]
        
        # Use Clearbit's logo API - this is a free service with generous limits
        return f"https://logo.clearbit.com/{domain}"
        
        # In a real implementation with web scraping, you would do:
        """
        # Make request to the website
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(f"https://{domain}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Look for img tags with class="logo"
            logo_pattern = r'<img[^>]*(?:class=["'][^"']*logo[^"']*["']|alt=["'][^"']*logo[^"']*["'])[^>]*src=["']([^"']+)["'][^>]*>'
            match = re.search(logo_pattern, response.text, re.I)
            
            if match and match.group(1):
                logo_url = match.group(1)
                
                # Handle relative URLs
                if logo_url.startswith('/'):
                    logo_url = f"https://{domain}{logo_url}"
                
                return logo_url
        
        return f"https://logo.clearbit.com/{domain}"  # Fallback to Clearbit
        """
    
    except Exception as e:
        st.error(f"Error extracting logo: {str(e)}")
        return f"https://via.placeholder.com/150?text=Error"

# Main app layout
st.title("Data Cleanup and Enhancement Tool")

# Initialize session state variables if they don't exist
if 'step' not in st.session_state:
    st.session_state.step = 1  # Current step in the process
if 'data' not in st.session_state:
    st.session_state.data = None  # DataFrame to store the data
if 'processed' not in st.session_state:
    st.session_state.processed = False  # Flag to indicate if data has been processed

# Create tabs for the different steps
tab1, tab2, tab3, tab4 = st.tabs(["1. Upload File", "2. Configure Columns", "3. Process Data", "4. Results & Export"])

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
            st.session_state.step = 2  # Move to next step
            
            st.success(f"File '{uploaded_file.name}' uploaded successfully!")
            st.write(f"Found {len(data.columns)} columns and {len(data)} rows.")
            
            # Preview the data
            st.subheader("Data Preview")
            st.dataframe(data.head())
            
            # Button to navigate to next step
            if st.button("Next: Configure Columns"):
                st.session_state.step = 2
                st.experimental_rerun()
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# Configure Columns Tab
with tab2:
    if st.session_state.data is not None:
        st.header("Configure Column Mappings")
        st.write("Select which columns in your data correspond to each field:")
        
        # Initialize column mappings if they don't exist
        if 'column_mappings' not in st.session_state:
            st.session_state.column_mappings = {
                'email': '',
                'website': '',
                'address': '',
                'city': '',
                'country': '',
                'logo': ''
            }
        
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
        
        # Navigation buttons
        col_back, col_next = st.columns([1, 1])
        
        with col_back:
            if st.button("Back"):
                st.session_state.step = 1
                st.experimental_rerun()
        
        with col_next:
            if st.button("Next: Process Data"):
                st.session_state.step = 3
                st.experimental_rerun()
    else:
        st.info("Please upload a file in the previous step.")

# Process Data Tab
with tab3:
    if st.session_state.data is not None and all(field in st.session_state.column_mappings for field in ['email', 'website', 'address', 'city', 'country', 'logo']):
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
                    
                    # Add a small delay to make progress visible
                    time.sleep(0.01)
                
                # Update session state with processed data
                st.session_state.data = processed_data
                st.session_state.processed = True
                
                # Complete progress bar
                progress_bar.progress(1.0)
                status_text.text("Processing complete!")
                
                # Success message
                st.success("Data processing completed successfully!")
                
                # Move to results tab
                st.session_state.step = 4
                st.experimental_rerun()
        
        # Navigation buttons
        col_back, _ = st.columns([1, 1])
        
        with col_back:
            if st.button("Back to Configure"):
                st.session_state.step = 2
                st.experimental_rerun()
    
    else:
        st.info("Please upload a file and configure columns in the previous steps.")

# Results & Export Tab
with tab4:
    if st.session_state.processed and st.session_state.data is not None:
        st.header("Results & Export")
        
        # Display the processed data
        st.subheader("Processed Data Preview")
        st.dataframe(st.session_state.data.head(10))
        
        if len(st.session_state.data) > 10:
            st.info(f"Showing 10 of {len(st.session_state.data)} rows. Export to view all data.")
        
        # Export options
        st.subheader("Export Options")
        
        col_csv, col_excel = st.columns(2)
        
        with col_csv:
            # Create a download button for CSV
            csv = st.session_state.data.to_csv(index=False)
            b64_csv = base64.b64encode(csv.encode()).decode()
            href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="processed_data.csv" class="btn">Download CSV File</a>'
            st.markdown(href_csv, unsafe_allow_html=True)
        
        with col_excel:
            # Create a download button for Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                st.session_state.data.to_excel(writer, index=False, sheet_name='Processed Data')
            
            buffer.seek(0)
            b64_excel = base64.b64encode(buffer.read()).decode()
            href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="processed_data.xlsx" class="btn">Download Excel File</a>'
            st.markdown(href_excel, unsafe_allow_html=True)
        
        # Navigation button
        if st.button("Process Another File"):
            # Reset session state
            st.session_state.data = None
            st.session_state.processed = False
            st.session_state.step = 1
            if 'column_mappings' in st.session_state:
                del st.session_state.column_mappings
            
            st.experimental_rerun()
    
    else:
        st.info("Please process data in the previous step.")

# Highlight the current step
if st.session_state.step == 1:
    tab1.title("1. Upload File")
elif st.session_state.step == 2:
    tab2.title("2. Configure Columns")
elif st.session_state.step == 3:
    tab3.title("3. Process Data")
elif st.session_state.step == 4:
    tab4.title("4. Results & Export")

# Add CSS for better styling
st.markdown("""
<style>
    .btn {
        display: inline-block;
        padding: 0.5em 1em;
        background-color: #4CAF50;
        color: white;
        text-align: center;
        text-decoration: none;
        font-size: 16px;
        border-radius: 4px;
        cursor: pointer;
        margin: 4px 2px;
    }
    .btn:hover {
        background-color: #45a049;
    }
</style>
""", unsafe_allow_html=True)
