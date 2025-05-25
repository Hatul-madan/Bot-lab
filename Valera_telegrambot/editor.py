
import json
import os

FILE = "characters.json"

def load_characters():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_characters(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def list_characters(data):
    print("\n📜 Персонажи:")
    for key in data:
        print(f"- {key}")
    print()

def add_character(data):
    name = input("🔤 Имя нового персонажа: ").strip()
    if name in data:
        print("⚠️ Такой персонаж уже есть.")
        return
    prompt = input("💬 Промпт: ").strip()
    data[name] = prompt
    save_characters(data)
    print("✅ Добавлен.")

def edit_character(data):
    name = input("✏️ Имя персонажа для редактирования: ").strip()
    if name not in data:
        print("❌ Нет такого персонажа.")
        return
    print(f"Текущий промпт:\n{data[name]}")
    prompt = input("💬 Новый промпт: ").strip()
    data[name] = prompt
    save_characters(data)
    print("✅ Изменено.")

def delete_character(data):
    name = input("🗑 Имя персонажа для удаления: ").strip()
    if name not in data:
        print("❌ Нет такого персонажа.")
        return
    del data[name]
    save_characters(data)
    print("🧹 Удалён.")

def main():
    while True:
        data = load_characters()
        print("\n==== Редактор персонажей ====")
        print("1 — Показать всех")
        print("2 — Добавить нового")
        print("3 — Изменить существующего")
        print("4 — Удалить")
        print("5 — Выйти")

        choice = input("👉 Твой выбор: ").strip()

        if choice == "1":
            list_characters(data)
        elif choice == "2":
            add_character(data)
        elif choice == "3":
            edit_character(data)
        elif choice == "4":
            delete_character(data)
        elif choice == "5":
            print("👋 Пока!")
            break
        else:
            print("❓ Неверный ввод")

if __name__ == "__main__":
    main()
