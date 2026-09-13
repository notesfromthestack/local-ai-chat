#!/usr/bin/env python
import httpx
import argparse


def post_request(addr: str, data: str, temperature: float, ):
    query_dict = {
        "model": "llama3.1:8b",
        "messages": [
            {"role": "user", "content": data}
        ],
        "temperature": temperature,
    }
    return httpx.post(addr, json=query_dict, timeout=None)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--addr", type=str, default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--data", type=str, default="What is a vector database?")
    parser.add_argument("--temperature", type=float, default=0.7)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = post_request(args.addr, args.data, args.temperature)
    print(result.json()["choices"][0]["message"]["content"])
