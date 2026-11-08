"""
BOBİ TV — YouTube Token Yenileme Modülü
OAuth refresh token ile access token otomatik yenilenir.
GitHub Secrets'tan token okur, yeniler, Actions ortamına yazar.
"""
import os
import json
import requests
import sys


def load_token() -> dict:
    """YOUTUBE_TOKEN secret'ından token verisi yükle."""
    raw = os.environ.get("YOUTUBE_TOKEN", "")
    if not raw:
        raise ValueError("YOUTUBE_TOKEN environment variable bulunamadı.")
    return json.loads(raw)


def refresh_access_token(token_data: dict) -> dict:
    """Refresh token kullanarak yeni access token al."""
    resp = requests.post(
        token_data["token_uri"],
        data={
            "client_id": token_data["client_id"],
            "client_secret": token_data["client_secret"],
            "refresh_token": token_data["refresh_token"],
            "grant_type": "refresh_token"
        },
        timeout=15
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Token yenileme başarısız: {resp.status_code} — {resp.text}")

    result = resp.json()
    if "access_token" not in result:
        raise RuntimeError(f"access_token yanıtta yok: {result}")

    token_data["token"] = result["access_token"]
    # Yeni refresh_token geldiyse güncelle
    if "refresh_token" in result:
        token_data["refresh_token"] = result["refresh_token"]

    return token_data


def verify_token(access_token: str) -> bool:
    """Token'ın geçerli olduğunu YouTube API ile doğrula."""
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    return resp.status_code == 200


def get_valid_token() -> str:
    """
    Geçerli access token döner.
    Mevcut token geçersizse yeniler.
    """
    token_data = load_token()
    access_token = token_data.get("token", "")

    # Mevcut token'ı test et
    if access_token and verify_token(access_token):
        return access_token

    # Geçersiz veya eksikse yenile
    print("[Token] Access token geçersiz, yenileniyor...")
    token_data = refresh_access_token(token_data)

    if not verify_token(token_data["token"]):
        raise RuntimeError("Yenilenen token da geçersiz. Manuel OAuth yenileme gerekli.")

    print("[Token] Token başarıyla yenilendi.")

    # GitHub Actions output'a yaz (workflow'da YOUTUBE_TOKEN secret güncellemek için)
    output_path = os.environ.get("GITHUB_OUTPUT", "")
    if output_path:
        with open(output_path, "a") as f:
            f.write(f"new_token={json.dumps(token_data)}\n")

    return token_data["token"]


def update_github_secret(new_token_data: dict, github_token: str, repo: str):
    """GitHub Secret'ı yeni token ile güncelle."""
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

    # Public key al
    pub_resp = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers={"Authorization": f"token {github_token}"},
        timeout=10
    )
    pub_resp.raise_for_status()
    pub_data = pub_resp.json()
    key_id = pub_data["key_id"]
    public_key_b64 = pub_data["key"]

    # libsodium ile şifrele
    from base64 import b64decode, b64encode
    from nacl.public import PublicKey, SealedBox

    public_key_bytes = b64decode(public_key_b64)
    sealed_box = SealedBox(PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(json.dumps(new_token_data).encode())
    encrypted_value = b64encode(encrypted).decode()

    # Secret'ı güncelle
    update_resp = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/YOUTUBE_TOKEN",
        headers={"Authorization": f"token {github_token}"},
        json={"encrypted_value": encrypted_value, "key_id": key_id},
        timeout=10
    )
    update_resp.raise_for_status()
    print("[Token] GitHub Secret güncellendi.")


if __name__ == "__main__":
    try:
        token = get_valid_token()
        print(f"[Token] Geçerli token alındı. (ilk 20 karakter: {token[:20]}...)")
        sys.exit(0)
    except Exception as e:
        print(f"[Token] HATA: {e}")
        sys.exit(1)
