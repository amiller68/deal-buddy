import anthropic
import json

def generate_summary(
        anthropic_client: anthropic.Client,
        pdf_text: str
) -> dict:
    prompt = """You are a real estate expert. Analyze the following real estate deal information and provide three sections:

1. Address: The property address
2. Title: A short descriptor of the property (1 line)
3. Description: A short description of the property that can fit in a blurb (2-3 sentences)
4. Summary: A 500-1000 word summary of the key features and relevant extractable data from the offering memorandum, including:
   - Property type and location
   - Size and key features
   - Current occupancy and major tenants
   - Financial highlights (e.g., asking price, NOI, cap rate)
   - Unique selling points or challenges
   - Market analysis
   - Investment highlights
   - Any other relevant information

Here's an example:

Input:
789 Industrial Way, Phoenix, AZ
Modern industrial facility located in Southwest Phoenix Industrial Park. Property consists of 150,000 SF warehouse with 32' clear height, built in 2020. Currently 100% leased to Amazon with 8 years remaining on triple-net lease. Property features 20 loading docks, ESFR sprinkler system, and 2.5 acres of trailer parking. Asking price $25M, current NOI $1.5M, representing a 6% cap rate. Located in rapidly growing industrial submarket with excellent access to I-10 and Loop 202.

Output:
{{
    \"address\": \"789 Industrial Way, Phoenix, AZ\",
    \"title\": \"Amazon-Leased Industrial Facility\",
    \"description\": \"Modern 150,000 SF industrial facility in Southwest Phoenix, built in 2020 and fully leased to Amazon. Features 32' clear height, 20 loading docks, and significant trailer parking in prime location near major highways.\",
    \"summary\": \"This institutional-quality industrial asset represents a secure investment opportunity in Phoenix's thriving Southwest industrial submarket. The 150,000 square foot facility was constructed in 2020 to modern specifications, featuring 32-foot clear heights, ESFR sprinkler systems, and 20 loading docks. The property sits on a generous parcel that includes 2.5 acres dedicated to trailer parking, a crucial amenity for major logistics operators. The facility is 100% leased to Amazon (S&P: AA) with 8 years remaining on a triple-net lease structure, providing stable, predictable cash flow with minimal landlord responsibilities. The asking price of $25 million, coupled with the current NOI of $1.5 million, represents a 6% cap rate, which is competitive for the market and credit quality. Located within the Southwest Phoenix Industrial Park, the property benefits from excellent transportation access via I-10 and Loop 202, crucial arteries for regional distribution. The Phoenix industrial market has seen robust growth, driven by population expansion, supply chain reorganization, and the continued rise of e-commerce. This submarket in particular has attracted numerous national logistics and distribution users. Investment highlights include: - Long-term lease to credit tenant - Modern construction with state-of-the-art features - Strategic location in growing industrial submarket - Triple-net lease structure minimizing owner responsibilities - Potential for rent growth at lease expiration given market trends. The Phoenix industrial market has maintained strong fundamentals with vacancy rates below 5% and consistent rent growth over the past five years. This property's location, tenant quality, and physical characteristics position it well to maintain its value and potentially capture additional upside as the market continues to mature.\"
}}

Now analyze this new property:

{pdf_text}

Provide your response in JSON format with keys address, title, description, and summary. Important: The summary should be a single line of text with no line breaks."""

    try:
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt.format(pdf_text=pdf_text)}],
        )

        print(response.content[0].text)
        result = response.content[0].text.strip()
        
        # Remove the markdown code block indicators if present
        if result.startswith("```json"):
            result = result[7:-3]  # Remove ```json and ``` 
        
        result = result.strip()
        result = json.loads(result)

        # Ensure all required keys are present
        required_keys = ["address", "title", "description", "summary"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key in response: {key}")

        return result
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise
    except ValueError as e:
        print(f"Value error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error in generate_summary: {e}")
        raise