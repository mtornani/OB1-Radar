"""Automated shame machine."""
import schedule
import time


def weekly_shame() -> None:
    """Run every Monday 9 AM UTC."""
    # Find worst transfers (placeholder)
    # Generate shame list
    # Post to Twitter/Reddit
    # Update website
    pass


if __name__ == "__main__":
    schedule.every().monday.at("09:00").do(weekly_shame)
    while True:
        schedule.run_pending()
        time.sleep(60)
