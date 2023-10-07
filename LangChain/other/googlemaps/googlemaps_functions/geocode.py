geocode_function = {
    "name": "geocode",
    "description": "",
    "parameters": {
        "type": "object",
        "properties": {
            "address": {
                "type": "string",
                "description": "The address to geocode.",
            },
            "language": {
                "type": "string",
                "description": "The language in which to return results."
            }
        },
        "required": ["address"]
    }
}