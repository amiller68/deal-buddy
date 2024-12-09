METADATA_PROMPT = """Extract key property metadata from this text.
Only extract fields if you are confident they are correct.
Leave fields empty if uncertain.

Return valid JSON in this format:
{{
    "title": "Official property name/title. THIS IS REQUIRED",
    "address": "Complete property address. THIS IS REQUIRED",
    "description": "2-3 sentence property overview. THIS IS REQUIRED",
    "square_feet": "Total square feet of the property if mentioned. THIS IS REQUIRED",
    "total_units": "Total number of units if mentioned. THIS IS REQUIRED",
    "property_type": "Type of property (e.g. multifamily, office). THIS IS REQUIRED",
}}

Text: {text}

Return valid JSON only."""

TABLE_DETECTION_PROMPT = """Identify and extract any tables from this text and any provided images. 
Known table types: rent_roll, expenses, units, occupancy

For each table found, normalize the data into a consistent format.
If you find a new table type, use an appropriate descriptive name.

Previous table types found: {known_tables}
Text: {text}

Respond with JSON in format:
{{
    "table_type": [
        {{normalized table rows as objects}}
    ]
}}

Return valid JSON only."""

SUMMARY_UPDATE_PROMPT = """Given the current summary and new text, update the summary.
Add any new relevant information while maintaining coherence.
Avoid redundancy and maintain a clear narrative flow.

Current summary: {current_summary}
New text: {new_text}

Provide only the updated summary text."""

PAGE_SCREENING_PROMPT = """Analyze this page and respond with JSON:
{{
    "is_relevant": boolean,  # Contains property data, financials, or key information. This includes rent rolls, expenses, units, occupancy, etc. This explicitly excludes generic marketing content and especially excludes confidentiality notices and legal disclaimers.
    "confidence": float,  # 0-1 score of confidence in assessment
    "reason": string  # Brief explanation of why you scored it this way
}}

Look for:
- Property details and descriptions
- Financial data and tables
- Market analysis
- Rent rolls or tenant information

Ignore:
- Legal disclaimers
- Confidentiality notices
- Generic marketing content
- Table of contents

Text: {text}

Return valid JSON only."""

CONFIDENTIALITY_FILTER_PROMPT = """Remove any confidentiality notices, disclaimers, or legal warnings from this text.
Return only the substantive content about the property or business.

Common patterns to remove:
- "Confidential Information"
- "Private & Confidential"
- Legal disclaimers about distribution
- Copyright notices
- Watermark text

Text: {text}

Return only the filtered content."""

METADATA_DETECTION_PROMPT = """Analyze if this text contains property document metadata.
Look for:
- Official property name/title
- Physical address
- Property description/overview
- Key property details

Respond with JSON:
{{
    "has_metadata": boolean,
    "confidence": float between 0-1,
    "reason": "Brief explanation of why you scored it this way"
}}"""
