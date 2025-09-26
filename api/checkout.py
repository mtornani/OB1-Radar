import os


def handler(request):  # Vercel signature
    payment_key = os.getenv("STRIPE_PUBLIC_KEY", "").strip()

    if not payment_key:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OB1 - Setup Required</title>
            <style>
                body { background: #000; color: #0f0; font-family: monospace; padding: 50px; }
                a { color: #0f0; }
            </style>
        </head>
        <body>
            <h1>PAYMENT SETUP REQUIRED</h1>
            <p>Add STRIPE_PUBLIC_KEY to Vercel environment variables to enable checkout.</p>
            <p>Revenue today: €0</p>
        </body>
        </html>
        """
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html; charset=utf-8"},
            "body": html,
        }

    return {
        "statusCode": 302,
        "headers": {
            "Location": f"https://checkout.stripe.com/pay/{payment_key}",
        },
    }
