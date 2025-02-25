import streamlit as st
import pandas as pd
import re
import requests
from io import BytesIO
import base64
from urllib.parse import urlparse
import time

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
                     'Armenia', 'Valledupar', 'Monteria', 'Sincelejo', 'Popayan', 'Palmira'],
        
        'Mexico': ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana', 'Leon', 'Juarez', 
                   'Merida', 'Chihuahua', 'Cancun', 'Queretaro', 'San Luis Potosi', 'Hermosillo', 
                   'Aguascalientes', 'Morelia', 'Veracruz', 'Mexicali', 'Culiacan', 'Acapulco'],
        
        'Brazil': ['Sao Paulo', 'Rio de Janeiro', 'Brasilia', 'Salvador', 'Fortaleza', 'Belo Horizonte', 
                   'Manaus', 'Curitiba', 'Recife', 'Porto Alegre', 'Belem', 'Goiania', 'Guarulhos', 
                   'Campinas', 'Sao Luis', 'Maceio', 'Duque de Caxias', 'Natal', 'Campo Grande'],
        
        'Chile': ['Santiago', 'Valparaiso', 'Concepcion', 'La Serena', 'Antofagasta', 'Temuco', 
                  'Rancagua', 'Talca', 'Arica', 'Iquique', 'Puerto Montt', 'Coquimbo', 'Osorno', 
                  'Quillota', 'Calama', 'Chillan', 'Valdivia', 'Punta Arenas', 'Copiapo'],
        
        # Add more countries and cities as needed
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
        
        # Use Clearbit's logo API
        return f"https://logo.clearbit.com/{domain}"
    
    except Exception as e:
        st.error(f"Error extracting logo: {str(e)}")
        return f"https://via.placeholder.com/150?text=Error"

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
        'logo': ''
    }
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0

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
            
            # Update current tab
            st.session_state.current_tab = 1
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
            csv = st.session_state.processed_data.to_csv(index=False)
            b64_csv = base64.b64encode(csv.encode()).decode()
            href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="processed_data.csv" class="btn">Download CSV File</a>'
            st.markdown(href_csv, unsafe_allow_html=True)
        
        with col_excel:
            # Create a download button for Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                st.session_state.processed_data.to_excel(writer, index=False, sheet_name='Processed Data')
            
            buffer.seek(0)
            b64_excel = base64.b64encode(buffer.read()).decode()
            href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="processed_data.xlsx" class="btn">Download Excel File</a>'
            st.markdown(href_excel, unsafe_allow_html=True)
        
        # Reset button
        if st.button("Process Another File"):
            # Reset session state
            st.session_state.data = None
            st.session_state.processed_data = None
            st.session_state.column_mappings = {
                'email': '',
                'website': '',
                'address': '',
                'city': '',
                'country': '',
                'logo': ''
            }
            st.session_state.current_tab = 0
            st.experimental_rerun()
    
    else:
        st.info("Please process data in the previous step.")

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
