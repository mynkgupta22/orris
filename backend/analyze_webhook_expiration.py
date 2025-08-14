"""
Script to understand webhook expiration times and Google Drive webhook duration
"""
import time
from datetime import datetime, timezone, timedelta

def analyze_webhook_expiration():
    """Analyze webhook expiration settings"""
    print("🔍 Webhook Expiration Analysis\n")

    # Test expiration value from our test
    test_expiration = "1755098913000"
    print(f"📅 Test expiration value: {test_expiration}")

    # Convert from milliseconds to datetime
    if test_expiration:
        try:
            exp_timestamp = int(test_expiration) / 1000  # Convert from milliseconds
            exp_date = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            print(f"   Expires on: {exp_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            # Calculate how long from now
            now = datetime.now(timezone.utc)
            time_diff = exp_date - now
            print(f"   Time until expiration: {time_diff}")

            if time_diff.total_seconds() > 0:
                days = time_diff.days
                hours = time_diff.seconds // 3600
                print(f"   That's approximately: {days} days and {hours} hours from now")
            else:
                print("   ⚠️  This expiration is in the past!")

        except Exception as e:
            print(f"   ❌ Error parsing expiration: {e}")

    print("\n" + "="*60)
    print("📖 Google Drive Webhook Expiration Information")
    print("="*60)

    # Current time for reference
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)

    print(f"🕒 Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Current timestamp (ms): {now_ms}")

    # Calculate what different expiration periods would look like
    print("\n📊 Webhook Duration Examples:")

    durations = [
        ("24 hours", 24 * 60 * 60),
        ("48 hours", 48 * 60 * 60), 
        ("7 days", 7 * 24 * 60 * 60),
        ("30 days", 30 * 24 * 60 * 60)
    ]

    for duration_name, seconds in durations:
        future_time = now + timedelta(seconds=seconds)
        future_ms = int(future_time.timestamp() * 1000)
        print(f"   {duration_name:10}: {future_ms} ({future_time.strftime('%Y-%m-%d %H:%M:%S UTC')})")

   

if __name__ == "__main__":
    analyze_webhook_expiration()