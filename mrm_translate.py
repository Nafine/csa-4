import base64
import dataclasses
import json
import zlib
from dataclasses import is_dataclass
from pathlib import Path

import requests

from translator.parser import ASTNode, Program


def generate_mermaid_ast(ast_node: Program) -> str:
    node_counter = 0
    lines = ["graph TD"]

    def get_new_id() -> str:
        nonlocal node_counter
        node_counter += 1
        return f"node{node_counter}"

    def escape(text: str) -> str:
        return str(text).replace('"', "&quot;")

    def traverse(node: ASTNode, parent_id: ASTNode | None = None, edge_label: str = "") -> None:
        if node is None:
            return

        current_id = get_new_id()

        if is_dataclass(node):
            node_type = type(node).__name__
            attributes = []
            children = []

            for field in dataclasses.fields(node):
                value = getattr(node, field.name)

                if isinstance(value, ASTNode):
                    children.append((value, field.name))

                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, ASTNode):
                            children.append((item, f"{field.name}[{i}]"))

                elif value is None:
                    continue

                else:
                    attributes.append(f"{field.name}={escape(value)}")

            label_parts = [f"<b>{node_type}</b>"] + attributes
            label_text = "<br>".join(label_parts)

            lines.append(f'    {current_id}["{label_text}"]')

            if parent_id:
                if edge_label:
                    lines.append(f'    {parent_id} -- "{edge_label}" --> {current_id}')
                else:
                    lines.append(f'    {parent_id} --> {current_id}')

            for child_node, child_edge_label in children:
                traverse(child_node, current_id, child_edge_label)

    traverse(ast_node)
    return "\n".join(lines)


def _encode_pako(mermaid_code: str) -> str:
    payload = json.dumps({"code": mermaid_code, "mermaid": {"theme": "default"}}, ensure_ascii=False)
    compressor = zlib.compressobj(9, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY)
    compressed = compressor.compress(payload.encode("utf-8")) + compressor.flush()
    return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")


def save_ast_to_png(mermaid_code: str, output_path: Path | None = None) -> None:
    if output_path is None:
        print("No output file provided to save diagram")
        return

    encoded = _encode_pako(mermaid_code)
    url = f"https://mermaid.ink/svg/pako:{encoded}"

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"Successfully saved: {output_path}")
        else:
            preview = response.text[:300] if response.text else ""
            print(f"Serverside error: ({response.status_code}): {preview}")

    except requests.RequestException as e:
        print(f"Error during request to mermaid.ink: {e}")
