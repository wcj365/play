import requests
import logging, configparser, pytz, os
from flask import Flask, request, Response
from xhtml2pdf import pisa
from io import BytesIO
from typing import List, Dict, Any, Optional
from datetime import datetime



# Fetch the discussions from the GitLab API
private_token = 'glpat-_vSqhhqSJypYJFwgz-jC'
project_id = '21983261'
merge_request_id = '1'
response = requests.get(
    f'https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{merge_request_id}/discussions',
    headers={'PRIVATE-TOKEN': private_token}
)
response.raise_for_status()
discussions = response.json()
print(discussions)

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
   # pdf = BytesIO()

    result_file = open(pdf_name, "w+b")
    pisa_status = pisa.CreatePDF(html, dest=result_file)

    return pisa_status


pisa_status = generate_code_review_pdf(discussions, "code_review.pdf") 
print(pisa_status)