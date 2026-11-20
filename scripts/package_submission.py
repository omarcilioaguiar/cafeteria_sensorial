"""Monta pacotes locais para revisão, sem publicar ou incluir credenciais e volumes."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "entrega"
DIRECTORIES = ("chat", "client", "common", "graos-service", "metodo-service",
               "degustacao-service", "mcp", "postgres", "scripts", "tests", "examples", "docs")
ROOT_FILES = ("README.md", "docker-compose.yml", ".env.example", "requirements-api.txt",
              "requirements-dev.txt", "pytest.ini")
EXCLUDED = {".venv", ".git", "__pycache__", ".pytest_cache", "node_modules", "cache", "historico"}
EXTENSIONS = {".py", ".js", ".css", ".html", ".json", ".md", ".txt", ".yml", ".sh",
              ".conf", ".tex", ".bib", ".png", ".jpg", ".pdf"}


def allowed(path):
    return (path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
            and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)
            and (not path.name.startswith(".env") or path.name == ".env.example")
            and (path.suffix in EXTENSIONS or path.name == "Dockerfile"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUT / "cafeteria-sensorial-fonte.zip", "w", ZIP_DEFLATED) as archive:
        for name in ROOT_FILES:
            path = ROOT / name
            if path.is_file():
                archive.write(path, f"cafeteria-sensorial/{name}")
        for directory in DIRECTORIES:
            for path in sorted((ROOT / directory).rglob("*")):
                if allowed(path):
                    archive.write(path, "cafeteria-sensorial/" + path.relative_to(ROOT).as_posix())
    chapter = ROOT / "docs" / "capitulo_cafeteria"
    with ZipFile(OUT / "capitulo-cafeteria.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted(chapter.rglob("*")):
            if allowed(path):
                archive.write(path, "capitulo_cafeteria/" + path.relative_to(chapter).as_posix())
    print("Pacotes preparados em artifacts/entrega. Revise conteúdo e pendências antes de publicar.")


if __name__ == "__main__":
    main()
