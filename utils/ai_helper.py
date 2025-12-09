def test_openai_api(api_key: str, message: str) -> dict:
    """Send a lightweight ping to OpenAI Responses API."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-5.1-2025-11-13",
            input=[
                {"role": "system", "content": "You are a helpful assistant. Please respond in Korean."},
                {"role": "user", "content": message},
            ],
            max_output_tokens=500,
        )

        return {"success": True, "message": response.output_text}

    except Exception as e:
        return {"success": False, "message": f"API 오류: {str(e)}"}
