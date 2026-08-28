MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

COMMON_PASSWORDS = {
    "123456",
    "12345678",
    "123456789",
    "admin",
    "admin123",
    "iloveyou",
    "letmein",
    "password",
    "password1",
    "password123",
    "qwerty",
    "qwerty123",
    "welcome",
}


def validate_password(password, username=None, email=None):
    errors = []

    if not isinstance(password, str):
        return ["密碼格式無效"]

    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"密碼至少需要 {MIN_PASSWORD_LENGTH} 個字元")
    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(f"密碼不得超過 {MAX_PASSWORD_LENGTH} 個字元")

    normalized_password = password.casefold()
    if normalized_password in COMMON_PASSWORDS:
        errors.append("密碼過於常見，請改用不容易猜測的密碼")

    character_classes = sum((
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    ))
    if character_classes < 3:
        errors.append("密碼需包含大寫字母、小寫字母、數字或符號中的至少三類")

    identity_values = [username]
    if email:
        identity_values.append(str(email).split("@", 1)[0])

    for identity in identity_values:
        normalized_identity = str(identity or "").strip().casefold()
        if len(normalized_identity) >= 3 and normalized_identity in normalized_password:
            errors.append("密碼不得包含帳號或 Email 名稱")
            break

    return errors


def password_error_response(password, username=None, email=None):
    errors = validate_password(password, username=username, email=email)
    if not errors:
        return None
    return {
        "error": errors[0],
        "code": "weak_password",
        "details": errors,
    }
