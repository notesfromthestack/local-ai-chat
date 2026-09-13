#!/usr/bin/env python
import httpx
import argparse


def post_request(addr: str, data: str, temperature: float, model: str, max_tokens: int | None = None,):
    query_dict = {
        "model": model,
        "messages": [
            {"role": "user", "content": data}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    return httpx.post(addr, json=query_dict, timeout=None)

def chat(addr: str, temperature: float, model: str, max_tokens: int | None = None, system_prompt: bool = False):
    messages = []
    if system_prompt:
        print("=========================================================")
        data = input("System prompt:\n")
        print("=========================================================")
        messages.append({"role": "system", "content": data})

    try:
        while True:
            print("=========================================================")
            data = input("You:\n")
            print("=========================================================")
            messages.append({"role": "user", "content": data})
            query_dict = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            respond = httpx.post(addr, json=query_dict, timeout=None)
            print(f'Assistant:\n{respond.json()["choices"][0]["message"]["content"]}')
            messages.append({"role": "assistant", "content": respond.json()["choices"][0]["message"]["content"]})
    except KeyboardInterrupt as e:
        return


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--addr", type=str, default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--data", type=str, default="What is a vector database?")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--model", type=str, default="llama3.1:8b")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--chat", action="store_true", default=False)
    parser.add_argument("--system-prompt", action="store_true", default=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.chat:
        chat(args.addr, args.temperature, args.model, args.max_tokens, args.system_prompt)
        exit(0)

    result = post_request(args.addr, args.data, args.temperature, args.model, args.max_tokens)
    print(result.json()["choices"][0]["message"]["content"])
