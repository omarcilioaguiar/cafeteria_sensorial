"""Ensaio real de embeddings, distância e persistência em coleção temporária."""
import json
import tempfile
from pathlib import Path

from semantic_cache import SemanticCache


def main():
    with tempfile.TemporaryDirectory() as folder:
        cache = SemanticCache(path=folder)
        cache.start()
        if cache.state != "ready":
            raise SystemExit("Cache não ficou pronto; ensaio não realizado.")
        original = "O que significa proporção entre café e água?"
        answer = "Proporção relaciona as massas de café e água no preparo."
        assert cache.store(original, answer, "ensaio")
        paraphrase = cache.lookup("Explique a proporção entre café e água.", "ensaio")
        assert paraphrase and paraphrase["answer"] == answer
        assert cache.lookup("Explique a proporção entre café e água.", "outro-modelo") is None
        assert cache.lookup("Explique a moagem do café.", "ensaio") is None
        report = {"state":"passed", "paraphrase_distance":paraphrase["distance"],
                  "distance_limit":cache.threshold, "model":cache.model_name,
                  "limitations":"Ensaio pequeno; não garante equivalência semântica de todas as perguntas."}
        target = Path("/app/data/avaliacao/cache.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
