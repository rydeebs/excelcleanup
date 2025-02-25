import React, { useState } from 'react';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import _ from 'lodash';

const DataCleanupTool = () => {
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('upload');
  
  // Column mapping state
  const [emailColumn, setEmailColumn] = useState('');
  const [websiteColumn, setWebsiteColumn] = useState('');
  const [addressColumn, setAddressColumn] = useState('');
  const [cityColumn, setCityColumn] = useState('');
  const [countryColumn, setCountryColumn] = useState('');
  const [logoColumn, setLogoColumn] = useState('');
  
  // Progress tracking
  const [progress, setProgress] = useState(0);
  
  // Function to handle file upload
  const handleFileUpload = (event) => {
    const uploadedFile = event.target.files[0];
    setFile(uploadedFile);
    setMessage(`File "${uploadedFile.name}" selected. Please proceed to the next step.`);
    
    // Read the file to extract headers
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        let result;
        
        if (uploadedFile.name.endsWith('.csv')) {
          // Parse CSV
          result = Papa.parse(e.target.result, {
            header: true,
            skipEmptyLines: true
          });
          
          setHeaders(result.meta.fields);
          setData(result.data);
        } else if (uploadedFile.name.endsWith('.xlsx') || uploadedFile.name.endsWith('.xls')) {
          // Parse Excel
          const workbook = XLSX.read(e.target.result, { type: 'binary' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          
          // Convert to JSON with headers
          result = XLSX.utils.sheet_to_json(worksheet);
          
          if (result.length > 0) {
            setHeaders(Object.keys(result[0]));
            setData(result);
          }
        }
        
        setMessage(`File parsed successfully. Found ${headers.length} columns and ${data.length} rows.`);
      } catch (error) {
        setMessage(`Error parsing file: ${error.message}`);
      }
    };
    
    if (uploadedFile.name.endsWith('.csv')) {
      reader.readAsText(uploadedFile);
    } else if (uploadedFile.name.endsWith('.xlsx') || uploadedFile.name.endsWith('.xls')) {
      reader.readAsBinaryString(uploadedFile);
    }
  };
  
  // Email validation and correction function based on username and website domain
  const validateAndCorrectEmail = async (email, country, website) => {
    if (!email && !website) return '';
    
    // Extract username part (before @)
    let username = '';
    if (email) {
      // If email contains @, get the part before it
      if (email.includes('@')) {
        username = email.split('@')[0].trim().toLowerCase();
      } else {
        // If no @, assume the entire string is the username
        username = email.trim().toLowerCase();
      }
    }
    
    // If no username was found, return empty
    if (!username) return '';
    
    // Get domain from website
    let domain = '';
    if (website) {
      try {
        // Clean up the website URL
        let websiteUrl = website.trim();
        if (!websiteUrl.match(/^https?:\/\//i)) {
          websiteUrl = 'https://' + websiteUrl;
        }
        
        // Parse the URL and extract domain
        const url = new URL(websiteUrl);
        domain = url.hostname.toLowerCase();
        
        // Remove 'www.' prefix if present
        domain = domain.replace(/^www\./i, '');
      } catch (e) {
        // If website parsing fails, try basic extraction
        domain = website.trim()
          .toLowerCase()
          .replace(/^https?:\/\//i, '')
          .replace(/^www\./i, '')
          .split('/')[0];
      }
    }
    
    // If still no domain, try to extract from email
    if (!domain && email && email.includes('@') && email.includes('.')) {
      domain = email.split('@')[1].trim().toLowerCase();
    }
    
    // If still no domain, use country TLD or default
    if (!domain) {
      const countryTLDs = {
        'Chile': 'domain.cl',
        'Brazil': 'domain.br',
        'Argentina': 'domain.ar',
        'Colombia': 'domain.co',
        'Mexico': 'domain.mx',
        'Peru': 'domain.pe',
        'United States': 'domain.com',
        'Canada': 'domain.ca',
        'United Kingdom': 'domain.uk',
        'Australia': 'domain.au',
        'Germany': 'domain.de',
        'France': 'domain.fr',
        'Italy': 'domain.it',
        'Spain': 'domain.es',
        'Portugal': 'domain.pt',
        'China': 'domain.cn',
        'Japan': 'domain.jp',
        'South Korea': 'domain.kr',
        'India': 'domain.in',
        'Russia': 'domain.ru'
      };
      
      domain = country && countryTLDs[country] ? countryTLDs[country] : 'domain.com';
    }
    
    // Construct the email
    return `${username}@${domain}`;
  };
  
  // Address cleanup function - parse through text to find valid street address
  const cleanupAddress = (addressText) => {
    if (!addressText) return '';
    
    // Common address patterns for various countries
    const patterns = [
      // Street number followed by street name
      /\b\d+\s+[A-Za-z\s]+\b(?:\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|court|ct|plaza|plz|square|sq|highway|hwy|route|rt))?/i,
      
      // Latin American address format (Calle, Carrera, Avenida, etc.)
      /\b(?:Calle|Cl|Carrera|Cr|Cra|Avenida|Av|Autopista|Diagonal|Transversal|Trans)\s+\d+\s*[A-Za-z0-9\s#\-°\.]+/i,
      
      // Building number or unit number
      /\b(?:Apt|Apartment|Unit|Suite|Ste|Building|Bldg|Floor|Fl|Room|Rm)\s+\d+[A-Za-z]?\b/i,
      
      // Hispanic style with # (e.g., "Calle 50 # 20-15")
      /\b(?:Calle|Cl|Carrera|Cr|Cra|Avenida|Av)\s+\d+\s*#\s*\d+(?:\s*-\s*\d+)?/i,
      
      // PO Box
      /\bP\.?O\.?\s*Box\s+\d+\b/i,
      
      // Generic number + word pattern (might catch some addresses)
      /\b\d+\s+[A-Za-z]{3,}\b/
    ];
    
    // Try to find address patterns in the text
    for (const pattern of patterns) {
      const match = addressText.match(pattern);
      if (match && match[0]) {
        // Found a potential address
        return match[0].trim();
      }
    }
    
    // If no patterns matched, look for any segment with numbers and letters that might be an address
    const segments = addressText.split(/[,;\n]+/);
    
    for (const segment of segments) {
      // Look for segments that have both numbers and letters (typical for addresses)
      if (/\d/.test(segment) && /[A-Za-z]/.test(segment) && segment.length > 5) {
        return segment.trim().replace(/\s+/g, ' ');
      }
    }
    
    // If still nothing found, return the first part of the text (limited to 50 chars)
    return addressText.trim().split(/[,;\n]/)[0].substring(0, 50).replace(/\s+/g, ' ');
  };
  
  // City extraction function - improved to find city names from address text
  const extractCity = (addressText, country) => {
    if (!addressText) return '';
    
    // Dictionary of major cities by country (simplified)
    const citiesByCountry = {
      'Colombia': ['Bogota', 'Medellin', 'Cali', 'Barranquilla', 'Cartagena', 'Cucuta', 'Bucaramanga', 'Pereira', 'Santa Marta', 'Manizales'],
      'Mexico': ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana', 'Leon', 'Juarez', 'Merida', 'Chihuahua', 'Cancun'],
      'Brazil': ['Sao Paulo', 'Rio de Janeiro', 'Brasilia', 'Salvador', 'Fortaleza', 'Belo Horizonte', 'Manaus', 'Curitiba', 'Recife', 'Porto Alegre'],
      'Chile': ['Santiago', 'Valparaiso', 'Concepcion', 'La Serena', 'Antofagasta', 'Temuco', 'Rancagua', 'Talca', 'Arica', 'Iquique'],
      'Argentina': ['Buenos Aires', 'Cordoba', 'Rosario', 'Mendoza', 'San Miguel de Tucuman', 'La Plata', 'Mar del Plata', 'Salta', 'Santa Fe', 'San Juan'],
      'Peru': ['Lima', 'Arequipa', 'Trujillo', 'Chiclayo', 'Piura', 'Iquitos', 'Cusco', 'Huancayo', 'Tacna', 'Juliaca'],
      'United States': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose'],
      'Canada': ['Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Edmonton', 'Ottawa', 'Winnipeg', 'Quebec City', 'Hamilton', 'Kitchener'],
      'Spain': ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Zaragoza', 'Malaga', 'Murcia', 'Palma', 'Las Palmas', 'Bilbao'],
      'United Kingdom': ['London', 'Birmingham', 'Manchester', 'Glasgow', 'Liverpool', 'Bristol', 'Sheffield', 'Leeds', 'Edinburgh', 'Leicester']
    };
    
    // Create a regex of cities for the given country (case insensitive)
    let cityPattern = null;
    if (country && citiesByCountry[country]) {
      const cityList = citiesByCountry[country];
      cityPattern = new RegExp(`\\b(${cityList.join('|')})\\b`, 'i');
      
      // First look for cities from our dictionary
      const match = addressText.match(cityPattern);
      if (match && match[0]) {
        return match[0].trim();
      }
    }
    
    // If no match with known cities, try some heuristics
    
    // Look for patterns like "City: X" or "X, City" or "City of X"
    const cityIndicatorPatterns = [
      /\bCity:\s*([A-Z][a-zA-Z\s]+)(?=[\s,;]|$)/i,
      /\b([A-Z][a-zA-Z\s]+),\s*(?:City|Town|Village|Municipality)(?=[\s,;]|$)/i,
      /\b(?:City|Town|Village|Municipality)\s+of\s+([A-Z][a-zA-Z\s]+)(?=[\s,;]|$)/i,
      /\b([A-Z][a-zA-Z\s]+)(?=\s*-\s*(?:Colombia|Mexico|Brazil|Chile|Argentina|Peru|United States|USA|Canada|Spain|UK))(?=[\s,;]|$)/i
    ];
    
    for (const pattern of cityIndicatorPatterns) {
      const match = addressText.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
    
    // Special case for "Medellin - Colombia" pattern as in the example
    const specialPattern = /\b([A-Z][a-zA-Z]+)\s*-\s*[A-Za-z]+\b/i;
    const specialMatch = addressText.match(specialPattern);
    if (specialMatch && specialMatch[1]) {
      return specialMatch[1].trim();
    }
    
    // Split by common delimiters and look for capitalized words that might be cities
    const parts = addressText.split(/[\s,;:\-\/]+/);
    const candidates = [];
    
    for (const part of parts) {
      // Skip empty or very short parts
      if (!part || part.length < 3) continue;
      
      // Check if it's capitalized and not a street type or direction
      if (
        part[0] === part[0].toUpperCase() &&
        !/^(St|Ave|Rd|Blvd|Ln|Dr|Ct|Plz|Sq|Hwy|Rt|North|South|East|West|NE|NW|SE|SW)$/i.test(part) &&
        !/^\d+$/.test(part) // Not just numbers
      ) {
        candidates.push(part);
      }
    }
    
    // Return the best candidate (preferring longer words, as they're more likely to be city names)
    if (candidates.length > 0) {
      candidates.sort((a, b) => b.length - a.length);
      return candidates[0];
    }
    
    return '';
  };
  
  // Function to extract logo from website using web scraping
  const extractLogoFromWebsite = async (website) => {
    if (!website) return '';
    
    try {
      // Simulate fetching website HTML (in a real implementation, you would use fetch or axios)
      // This is a mock implementation for demo purposes
      const mockScrapingResponse = async (url) => {
        // Simulate a network request delay
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Create a random success rate for demo purposes
        const success = Math.random() > 0.3;
        
        if (!success) {
          throw new Error('Failed to fetch website content');
        }
        
        // Return mock HTML content
        return `
          <!DOCTYPE html>
          <html>
          <head>
            <title>Company Website</title>
          </head>
          <body>
            <header>
              <div class="logo-container">
                <img class="logo" src="https://example.com/logo.png" alt="Company Logo">
              </div>
              <nav>...</nav>
            </header>
            <main>...</main>
          </body>
          </html>
        `;
      };
      
      // Clean up website URL
      let websiteUrl = website.trim();
      if (!websiteUrl.match(/^https?:\/\//i)) {
        websiteUrl = 'https://' + websiteUrl;
      }
      
      // Fetch website content
      const html = await mockScrapingResponse(websiteUrl);
      
      // Parse HTML to find logo (simplified for demo)
      // Look for img tags with class="logo" or containing "logo" in their classes
      const logoRegex = /<img[^>]*(?:class=["'][^"']*logo[^"']*["']|alt=["'][^"']*logo[^"']*["'])[^>]*src=["']([^"']+)["'][^>]*>/i;
      const match = html.match(logoRegex);
      
      if (match && match[1]) {
        // Found a logo image URL
        let logoUrl = match[1];
        
        // Handle relative URLs
        if (logoUrl.startsWith('/')) {
          const urlObj = new URL(websiteUrl);
          logoUrl = `${urlObj.protocol}//${urlObj.hostname}${logoUrl}`;
        }
        
        // In a real implementation, you would download and convert the image
        // For demo purposes, return a placeholder with the domain name
        const domain = new URL(websiteUrl).hostname.replace('www.', '');
        return `/api/placeholder/64/64?text=${encodeURIComponent(domain)}`;
      }
      
      // Fallback search for any img tag that might be a logo
      const fallbackRegex = /<img[^>]*src=["']([^"']+logo[^"']+)["'][^>]*>/i;
      const fallbackMatch = html.match(fallbackRegex);
      
      if (fallbackMatch && fallbackMatch[1]) {
        // Found a possible logo by URL containing "logo"
        return `/api/placeholder/64/64?text=${encodeURIComponent('Found')}`;
      }
      
      // Couldn't find a logo
      return `/api/placeholder/64/64?text=${encodeURIComponent('No Logo')}`;
      
    } catch (error) {
      console.error('Error extracting logo:', error);
      return `/api/placeholder/64/64?text=${encodeURIComponent('Error')}`;
    }
  };
  
  // Process the data
  const processData = async () => {
    if (!data.length) {
      setMessage('Please upload a file first.');
      return;
    }
    
    setProcessing(true);
    setProgress(0);
    
    try {
      const processedData = [...data];
      
      for (let i = 0; i < processedData.length; i++) {
        const row = processedData[i];
        
        // Update progress
                  setProgress(Math.floor((i / processedData.length) * 100));
          setMessage(`Processing row ${i+1} of ${processedData.length}...`);
        
        // Process email if column selected
        if (emailColumn && websiteColumn && countryColumn) {
          row[emailColumn] = await validateAndCorrectEmail(
            row[emailColumn] || '', 
            row[countryColumn] || '', 
            row[websiteColumn] || ''
          );
        }
        
        // Clean up address if column selected
        if (addressColumn) {
          row[addressColumn] = cleanupAddress(row[addressColumn] || '');
        }
        
        // Extract city if columns selected
        if (cityColumn && addressColumn && countryColumn) {
          row[cityColumn] = extractCity(row[addressColumn] || '', row[countryColumn] || '');
        }
        
        // Extract logo if columns selected
        if (logoColumn && websiteColumn) {
          row[logoColumn] = extractLogoFromWebsite(row[websiteColumn] || '');
        }
      }
      
      setData(processedData);
      setProgress(100);
      setMessage('Data processing completed successfully.');
      setActiveTab('results');
    } catch (error) {
      setMessage(`Error processing data: ${error.message}`);
    } finally {
      setProcessing(false);
    }
  };
  
  // Export function
  const exportData = (format) => {
    if (!data.length) {
      setMessage('No data to export.');
      return;
    }
    
    try {
      if (format === 'csv') {
        // Export as CSV
        const csv = Papa.unparse(data);
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        // Create download link
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'processed_data.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (format === 'xlsx') {
        // Export as Excel
        const worksheet = XLSX.utils.json_to_sheet(data);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Processed Data');
        XLSX.writeFile(workbook, 'processed_data.xlsx');
      }
      
      setMessage(`Data exported successfully as ${format.toUpperCase()}.`);
    } catch (error) {
      setMessage(`Error exporting data: ${error.message}`);
    }
  };
  
  return (
    <div className="w-full max-w-6xl mx-auto p-4 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6 text-center">Data Cleanup and Enhancement Tool</h1>
      
      {/* Navigation Tabs */}
      <div className="flex border-b mb-4">
        <button 
          className={`px-4 py-2 ${activeTab === 'upload' ? 'bg-blue-500 text-white' : 'bg-gray-200'} rounded-t-lg mr-1`}
          onClick={() => setActiveTab('upload')}
        >
          1. Upload File
        </button>
        <button 
          className={`px-4 py-2 ${activeTab === 'configure' ? 'bg-blue-500 text-white' : 'bg-gray-200'} rounded-t-lg mr-1`}
          onClick={() => headers.length > 0 ? setActiveTab('configure') : setMessage('Please upload a file first')}
        >
          2. Configure Columns
        </button>
        <button 
          className={`px-4 py-2 ${activeTab === 'process' ? 'bg-blue-500 text-white' : 'bg-gray-200'} rounded-t-lg mr-1`}
          onClick={() => headers.length > 0 ? setActiveTab('process') : setMessage('Please upload a file first')}
        >
          3. Process Data
        </button>
        <button 
          className={`px-4 py-2 ${activeTab === 'results' ? 'bg-blue-500 text-white' : 'bg-gray-200'} rounded-t-lg`}
          onClick={() => data.length > 0 ? setActiveTab('results') : setMessage('No data to display')}
        >
          4. Results & Export
        </button>
      </div>
      
      {/* Message Display */}
      {message && (
        <div className={`p-3 mb-4 rounded ${message.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
          {message}
        </div>
      )}
      
      {/* Upload Tab */}
      {activeTab === 'upload' && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Upload Your File</h2>
          <p className="mb-4">Supported formats: CSV, Excel (.xlsx, .xls)</p>
          
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
                <p className="mb-2 text-sm text-gray-500"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                <p className="text-xs text-gray-500">CSV, XLS, or XLSX</p>
              </div>
              <input 
                type="file" 
                className="hidden" 
                accept=".csv,.xlsx,.xls" 
                onChange={handleFileUpload}
              />
            </label>
          </div>
          
          {file && (
            <div className="mt-4">
              <p><strong>Selected file:</strong> {file.name}</p>
              <button 
                className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                onClick={() => headers.length > 0 ? setActiveTab('configure') : null}
              >
                Next: Configure Columns
              </button>
            </div>
          )}
        </div>
      )}
      
      {/* Configure Tab */}
      {activeTab === 'configure' && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Configure Column Mappings</h2>
          <p className="mb-4">Select which columns in your data correspond to each field:</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Email Column:</label>
              <select 
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                value={emailColumn} 
                onChange={(e) => setEmailColumn(e.target.value)}
              >
                <option value="">Select a column</option>
                {headers.map((header) => (
                  <option key={`email-${header}`} value={header}>{header}</option>
                ))}
              </select>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Website Column:</label>
              <select 
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                value={websiteColumn} 
                onChange={(e) => setWebsiteColumn(e.target.value)}
              >
                <option value="">Select a column</option>
                {headers.map((header) => (
                  <option key={`website-${header}`} value={header}>{header}</option>
                ))}
              </select>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Address Column:</label>
              <select 
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                value={addressColumn} 
                onChange={(e) => setAddressColumn(e.target.value)}
              >
                <option value="">Select a column</option>
                {headers.map((header) => (
                  <option key={`address-${header}`} value={header}>{header}</option>
                ))}
              </select>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">City Column:</label>
              <select 
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                value={cityColumn} 
                onChange={(e) => setCityColumn(e.target.value)}
              >
                <option value="">Select a column</option>
                {headers.map((header) => (
                  <option key={`city-${header}`} value={header}>{header}</option>
                ))}
              </select>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Country Column:</label>
              <select 
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                value={countryColumn} 
                onChange={(e) => setCountryColumn(e.target.value)}
              >
                <option value="">Select a column</option>
                {headers.map((header) => (
                  <option key={`country-${header}`} value={header}>{header}</option>
                ))}
              </select>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Logo Column:</label>
              <select 
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                value={logoColumn} 
                onChange={(e) => setLogoColumn(e.target.value)}
              >
                <option value="">Select a column</option>
                {headers.map((header) => (
                  <option key={`logo-${header}`} value={header}>{header}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="mt-4 flex justify-between">
            <button 
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              onClick={() => setActiveTab('upload')}
            >
              Back
            </button>
            <button 
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => setActiveTab('process')}
            >
              Next: Process Data
            </button>
          </div>
        </div>
      )}
      
      {/* Process Tab */}
      {activeTab === 'process' && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Process Data</h2>
          
          <div className="mb-6">
            <h3 className="font-medium mb-2">Selected Configuration:</h3>
            <ul className="list-disc pl-6">
              {emailColumn && <li>Email: {emailColumn}</li>}
              {websiteColumn && <li>Website: {websiteColumn}</li>}
              {addressColumn && <li>Address: {addressColumn}</li>}
              {cityColumn && <li>City: {cityColumn}</li>}
              {countryColumn && <li>Country: {countryColumn}</li>}
              {logoColumn && <li>Logo: {logoColumn}</li>}
            </ul>
          </div>
          
          <div className="mb-4">
            <h3 className="font-medium mb-2">Processing Tasks:</h3>
            <ul className="list-disc pl-6">
              {emailColumn && websiteColumn && countryColumn && (
                <li>Validate and correct email addresses in column "{emailColumn}"</li>
              )}
              {addressColumn && (
                <li>Clean up addresses in column "{addressColumn}"</li>
              )}
              {cityColumn && addressColumn && countryColumn && (
                <li>Extract cities from addresses and update column "{cityColumn}"</li>
              )}
              {logoColumn && websiteColumn && (
                <li>Extract company logos from websites and update column "{logoColumn}"</li>
              )}
            </ul>
          </div>
          
          {processing && (
            <div className="mb-4">
              <p>Processing... {progress}%</p>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full" 
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}
          
          <div className="mt-6 flex justify-between">
            <button 
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              onClick={() => setActiveTab('configure')}
              disabled={processing}
            >
              Back
            </button>
            <button 
              className={`px-4 py-2 ${processing ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'} text-white rounded`}
              onClick={processData}
              disabled={processing}
            >
              {processing ? 'Processing...' : 'Process Data Now'}
            </button>
          </div>
        </div>
      )}
      
      {/* Results Tab */}
      {activeTab === 'results' && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Results & Export</h2>
          
          <div className="mb-4">
            <div className="flex justify-end space-x-2 mb-4">
              <button 
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                onClick={() => exportData('csv')}
              >
                Export as CSV
              </button>
              <button 
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                onClick={() => exportData('xlsx')}
              >
                Export as Excel
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full bg-white border border-gray-300">
                <thead>
                  <tr className="bg-gray-100">
                    {headers.map((header) => (
                      <th key={header} className="py-2 px-4 border-b text-left">
                        {header}
                        {header === emailColumn && ' ✓'}
                        {header === addressColumn && ' ✓'}
                        {header === cityColumn && ' ✓'}
                        {header === logoColumn && ' ✓'}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.slice(0, 5).map((row, rowIndex) => (
                    <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                      {headers.map((header) => (
                        <td key={`${rowIndex}-${header}`} className="py-2 px-4 border-b">
                          {header === logoColumn && row[header] ? (
                            <img src={row[header]} alt="Logo" className="w-8 h-8" />
                          ) : (
                            String(row[header] || '')
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {data.length > 5 && (
              <p className="mt-2 text-gray-600 text-sm">
                Showing 5 of {data.length} rows. Export to view all data.
              </p>
            )}
          </div>
          
          <div className="mt-4">
            <button 
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              onClick={() => setActiveTab('process')}
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataCleanupTool;
