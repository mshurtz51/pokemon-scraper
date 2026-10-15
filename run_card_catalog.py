"""Ingest a structured card catalog set into the project database."""

import argparse

from src.card_catalog import ingest_block, ingest_set


def main():
    parser = argparse.ArgumentParser(
        description="Ingest card metadata and official image URLs for one set."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--set-code",
        help="Catalog or RK9 set code, such as me01 or MEG.",
    )
    selection.add_argument(
        "--block",
        choices=["me", "sv"],
        help="Ingest every expansion in a block (me or sv).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Concurrent detail requests (default: 8).",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Fetch one detail request per card; slower but more complete.",
    )
    args = parser.parse_args()

    if args.block:
        results = ingest_block(
            block=args.block,
            workers=max(1, args.workers),
            details=args.details,
        )

        for result in results:
            print(
                f"{result['set_code']}: "
                f"{result['catalog_cards']} catalog cards, "
                f"{result['linked_deck_cards']} linked deck-card rows"
            )
    else:
        result = ingest_set(
            set_code=args.set_code or "me01",
            workers=max(1, args.workers),
            details=True,
        )

        print(f"Set: {result['set_code']}")
        print(f"Catalog cards stored: {result['catalog_cards']}")
        print(f"Deck-card rows linked: {result['linked_deck_cards']}")


if __name__ == "__main__":
    main()
