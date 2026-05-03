import json
import secrets

REVIEWERS = [
    
    "Тарасов А.А.",
    "Рецензент 2",
    "Рецензент 3",
    "Рецензент 4",
    "Рецензент 5",
    "Рецензент 6",
    "Рецензент 7",
    "Рецензент 8",
    "Рецензент 9",
    "Рецензент 10",
]


def generate_key() -> str:
    """Случайный 32-символьный ключ — нечитаемый, неугадываемый."""
    return secrets.token_urlsafe(24)


def main():
    pairs = [(name, generate_key()) for name in REVIEWERS]

    # 1. Файл для бэкенда — только сами ключи
    with open("api_keys.json", "w", encoding="utf-8") as f:
        json.dump({"keys": [k for _, k in pairs]}, f, indent=2)
    print("✓ Создан api_keys.json (для бэкенда)")

    # 2. Шпаргалка — кому какой ключ выдать
    with open("reviewer_keys.txt", "w", encoding="utf-8") as f:
        f.write("РЕЦЕНЗЕНТ → API-КЛЮЧ\n")
        f.write("=" * 70 + "\n\n")
        for name, key in pairs:
            f.write(f"{name}\n  {key}\n\n")
    print("✓ Создан reviewer_keys.txt (кому какой ключ выдать)")


if __name__ == "__main__":
    main()
