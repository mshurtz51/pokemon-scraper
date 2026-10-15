"""Create the representative-card archetype contact sheet."""

from src.visualizations.archetype_cards import (
    create_archetype_card_contact_sheet,
)


def main():
    result = create_archetype_card_contact_sheet()

    print(f"Archetype rows rendered: {result['archetype_rows']}")
    print(f"Configured card IDs: {result['configured_card_ids']}")
    print(f"PNG: {result['png_path']}")
    print(f"PDF: {result['pdf_path']}")

    missing = result["missing_card_ids"]

    if missing.empty:
        print("Card ID validation: all configured IDs resolved.")
    else:
        print("Card ID validation: missing IDs")
        print(missing.to_string(index=False))

    image_failures = result["image_failures"]

    if image_failures.empty:
        print("Image validation: all configured cards loaded.")
    else:
        print("Image validation: unavailable assets")
        print(image_failures.to_string(index=False))


if __name__ == "__main__":
    main()
