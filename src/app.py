"""
This Flask application receives a list of GitLab discussions as a part of a POST request, processes the 
discussions and generates a PDF file with the relevant information. The application then returns this PDF 
to the client. This is designed to work in environments where the Flask server may not have direct access 
to the GitLab server, and thus requires the GitLab data to be passed along with the HTTP request.

Key components of the application include:

1. handle_generate_pdf() view: This is the main endpoint of the application that listens to POST requests. 
    It first checks the API key for authentication. If the key is valid, it proceeds to read the request 
    body for the GitLab discussions data. If the data is in the correct format, it invokes the 
    generate_code_review_pdf() function to create a PDF and then sends this PDF back to the client. It 
    also includes robust error handling to manage cases where the API key is invalid or the request body 
    is in an incorrect format.

2. generate_code_review_pdf() function: This function takes the discussions data and the name for the PDF 
as input. It converts the data into an HTML string, with each discussion represented in a specific format. 
The function then uses the xhtml2pdf library to convert this HTML string into a PDF. The resulting PDF is 
then returned as a BytesIO object.

3. send_pdf_response() function: This function takes a BytesIO object and a filename as input. It reads 
the bytes from the BytesIO object, creates a Flask response object with the appropriate headers to make 
the file downloadable, and then sends this response object back to the client.

4. convert_utc_to_est() function: This function is a utility function that helps in converting the timestamp 
data from UTC to EST, which is then used in the generate_code_review_pdf() function.

The application also incorporates logging mechanisms to track the API keys used for requests. This allows 
for monitoring and auditing of the use of the API endpoint.
"""

import logging, configparser, pytz, os
from flask import Flask, request, Response
from xhtml2pdf import pisa
from io import BytesIO
from typing import List, Dict, Any, Optional
from datetime import datetime


app = Flask(__name__)

# Initialize logger
logger = logging.getLogger('api')
handler = logging.FileHandler('api.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Define a default key
DEFAULT_KEY = "1840ca99-74ac-45d2-8476-3baf66f64125"

# Load the API keys into memory
def load_api_keys(file):
    if os.path.isfile(file):
        config = configparser.ConfigParser()
        config.read(file)
        return list(config['API_KEYS'].values())
    else:
        return [DEFAULT_KEY]

VALID_API_KEYS = load_api_keys('config.ini')

# print(VALID_API_KEYS)

def convert_utc_to_est(utc_timestamp_str: Optional[str]) -> Optional[str]:
    """
    Convert a UTC timestamp string to an Eastern Time timestamp string.

    This function parses the input UTC timestamp string to a datetime object,
    sets the timezone of the timestamp to UTC, converts the timestamp to Eastern Time,
    and then formats and returns the timestamp as a string.

    Args:
        utc_timestamp_str: A string representing a timestamp in UTC. 
        The string should be in the format: "%Y-%m-%dT%H:%M:%S.%fZ".
        This is the default timezone and format that ships from gitlab.

    Returns:
        A string representing the input timestamp converted to Eastern Time, 
        in the format: "%Y-%m-%d %H:%M:%S". 
        Returns None if the input string is None.

    Raises:
        ValueError: If the input string is not in the expected format.
    """
    if utc_timestamp_str is None:
        return None
        
    # Parse the UTC timestamp string to a datetime object
    utc_timestamp = datetime.strptime(utc_timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")

    # Set the timezone of the timestamp to UTC
    utc_timestamp = utc_timestamp.replace(tzinfo=pytz.UTC)

    # Convert to Eastern Time
    est_timestamp = utc_timestamp.astimezone(pytz.timezone('America/New_York'))

    # Format the timestamp
    formatted_timestamp = est_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_timestamp



def generate_code_review_pdf(discussions: List[Dict[str, Any]], pdf_name: str) -> Optional[BytesIO]:

    """
    Generate a PDF file of GitLab code review comments from a list of discussions.

    This function creates an HTML string with the content of the discussions, each formatted as a table row,
    and converts this HTML string to a PDF file, which is returned as a BytesIO object.

    Args:
        discussions: A list of dictionaries, each representing a discussion from a GitLab merge request.
                     Each dictionary should contain a 'notes' key, which is a list of note dictionaries. 
                     Each note dictionary should include 'author', 'avatar_url', 'created_at', 'username',
                     'web_url', 'name', and 'body' keys.

        pdf_name: A string that will be used as the title of the PDF document.

    Returns:
        A BytesIO object representing the generated PDF file.

    Raises:
        ValueError: If a key is missing in the discussions or notes dictionaries.
    """

    # Start the HTML string
    html = f'''
    <!DOCTYPE html>
    <html>
    <body>
    <h1>{pdf_name}</h1>
    <p style="text-align: right;">{datetime.now(pytz.timezone('America/New_York')).strftime("%Y-%m-%d %H:%M:%S")}</p>
    '''

    for discussion in discussions:
        notes = discussion['notes']
        first_note = notes[0]
        author = first_note['author']
        avatar_url = author['avatar_url']
        timestamp = convert_utc_to_est(first_note['created_at'])
        username = author['username']
        web_url = author['web_url']
        name = author['name']

        # Unfortunately, a great deal of styles are not supported by xhtml2pdf...
        # https://xhtml2pdf.readthedocs.io/en/latest/reference.html#supported-css-properties

        html += f'''
        <hr>
        <table style="width: 100%;">
            <tr>
                <td style="width: 30px; padding-right: 10px; vertical-align: top;">
                    <div style="height: 30px; width: 30px; overflow: hidden;">
                        <img src="{avatar_url}" alt="Avatar" style="height: 30px; width: 30px;">
                    </div>
                </td>
                <td style="vertical-align: top;">
                    <p>{name} <a href="{web_url}">@{username}</a></p>
                    <p><strong>{discussion["id"]}</strong>: {first_note["body"]}</p>
        '''

        for note in notes[1:]:

            _author = note['author']
            _avatar_url = _author['avatar_url']
            _timestamp = convert_utc_to_est(note['created_at'])
            _username = _author['username']
            _web_url = _author['web_url']
            _name = _author['name']

            html += f'''
                    <hr style="border-top: 1px dotted #000; color: transparent; background-color: transparent; height: 1px; width:100%;">
                    <table>
                        <tr>
                            <td style="width: 30px;"><img src="{_avatar_url}" alt="Avatar" style="height: 10px; width: 10px;"></td>
                            <td>{_name} <a href="{_web_url}">@{_username}</a></td>
                            <td style="text-align: right; vertical-align: top;">{_timestamp}</td>
                        </tr>
                        <tr>
                            <td colspan="3"><p style='word-break: break-all;'>{note["body"]}</p></td>
                        </tr>
                    </table>
                    '''

        html += f'''
                </td>
                <td style="text-align: right; vertical-align: top;">
                    <p>{timestamp}</p>
                </td>
            </tr>
        </table>
        '''
    # End the HTML string
    html += """
    </body>
    </html>
    """

    # Convert the HTML to a PDF
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf)

    return pdf

@app.route('/generate_pdf', methods=['POST'])
def handle_generate_pdf():
    """
    Handle a POST request to generate a PDF of GitLab code review comments.

    This function expects the request to include a JSON body with a key 'discussions' 
    that contains an array of discussions from a GitLab merge request. Each discussion 
    should be a dictionary with the same structure as the objects returned by the 
    GitLab API's discussions endpoint.

    An optional 'name' field can be included in the JSON body to set a custom name 
    for the PDF. If no name is provided, the default name 'Code Review Comments' is used.

    The request must also include a valid API key in the 'X-API-KEY' header.

    Returns:
        - A PDF file of the code review comments, or
        - A JSON object with an 'error' key and a status code of 400 if the request is 
          missing necessary data, or
        - A JSON object with an 'error' key and a status code of 401 if an invalid API 
          key is provided.
    """

    if request.method != 'POST':
        return {'error': 'Invalid request method'}, 405

    api_key = request.headers.get('X-API-KEY')
    if api_key not in VALID_API_KEYS:
        logger.info('Invalid API key used: {}'.format(api_key))
        return {'error': 'Invalid API key'}, 401

    logger.info('API key used: {}'.format(api_key))

    if not request.json:
        return {'error': 'Missing body in request'}, 400

    data = request.json
    if 'discussions' not in data:
        return {'error': 'Missing discussions in request'}, 400
    discussions = data['discussions']

    pdf_name = data.get('name', 'Code Review Comments')

    pdf = generate_code_review_pdf(discussions, pdf_name)
    pdf.seek(0)

    return send_pdf_response(pdf, "code_review.pdf")

def send_pdf_response(pdf_bytes: BytesIO, filename: str) -> Any:
    """
    Create a Flask response object to send a PDF file as a downloadable attachment.

    This function reads the bytes from a BytesIO object representing a PDF file, 
    sets the appropriate headers to make the file downloadable, 
    and returns a Flask response object with these settings.

    Args:
        pdf_bytes: A BytesIO object representing the PDF file to send.
        filename: A string to be used as the name of the downloaded file.

    Returns:
        A Flask response object that, when returned from a Flask route, 
        will send a downloadable PDF file to the client.
    """
    response = Response(pdf_bytes.read(),
                        mimetype="application/pdf",
                        headers={"Content-disposition":
                                     f"attachment; filename={filename}"})
    return response

if __name__ == "__main__":
    app.run(debug=True)
