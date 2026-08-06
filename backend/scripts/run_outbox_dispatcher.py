from app.services.outbox_dispatcher import run_dispatcher_forever


def main() -> None:
    run_dispatcher_forever()


if __name__ == "__main__":
    main()
