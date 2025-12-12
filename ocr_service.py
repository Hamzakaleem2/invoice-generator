import base64
import json
from mistralai import Mistral

def analyze_with_mistral(image_file, api_key):
    """
    Service to send image to Mistral AI and parse the JSON response.
    """
    if not api_key:
        return None, "Please enter API Key."
    
    try:
        # Encode image
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        image_file.seek(0) # Reset pointer
        
        client = Mistral(api_key=api_key)
        
        prompt = """
        Extract from this Purchase Order image:
        {
            "po_no": "Order No string",
            "date": "DD.MM.YYYY",
            "buyer": "Buyer Title (e.g. Project Director)",
            "dept": "Department Name",
            "items": [
                {"Qty": number, "Description": "string", "Rate": number}
            ]
        }
        Return ONLY JSON.
        """
        
        resp = client.chat.complete(
            model="pixtral-12b-2409",
            messages=[{
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                ]
            }]
        )
        
        content = resp.choices[0].message.content
        
        # Clean JSON markdown
        if "```" in content:
            content = content.split("```json")[-1].split("```")[0]
            
        return json.loads(content.strip()), None

    except Exception as e:
        return None, f"AI Error: {str(e)}"
