def test_chat(client):
    test_data = {
        "model": "llama3.1:8b",
        "messages": [
            {"role": "user", "content": "Hi"}
        ],
        "temperature": 0.7,
    }
    response = client.post("/v1/chat/completions", json=test_data)
    assert response.status_code == 200
    response_json = response.json()
    assert "choices" in response_json
    assert "id" in response_json
    assert "model" in response_json
    assert "created" in response_json
    assert "object" in response_json
    assert "message" in response_json["choices"][0]
    assert "finish_reason" in response_json["choices"][0]
    assert "index" in response_json["choices"][0]
    assert "content" in response_json["choices"][0]["message"]
    assert "role" in response_json["choices"][0]["message"]


def test_chat_no_messages(client):
    test_data = {
        "model": "llama3.1:8b",
        "messages": [],
        "temperature": 0.7,
    }
    response = client.post("/v1/chat/completions", json=test_data)
    assert response.status_code == 400


def test_chat_includes_usage_statistics(client):
    test_data = {
        "model": "llama3.1:8b",
        "messages": [
            {"role": "user", "content": "Hi"}
        ],
    }
    response = client.post("/v1/chat/completions", json=test_data)
    assert response.status_code == 200
    response_json = response.json()

    assert "usage" in response_json
    assert "prompt_tokens" in response_json["usage"]
    assert "completion_tokens" in response_json["usage"]
    assert "total_tokens" in response_json["usage"]