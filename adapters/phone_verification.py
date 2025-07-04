def check_phone_verified(request) -> bool:
    """
    Placeholder: check request header or session cookie.
    In production, check your database or external auth provider.
    """
    phone_verified = request.headers.get("X-Phone-Verified", "false").lower() == "true"
    print(f"[Modelex] Phone verified: {phone_verified}")
    return phone_verified
