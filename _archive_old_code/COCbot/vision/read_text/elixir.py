import cv2

from COCbot.vision.read_text.numbers import read_number

IMAGE_PATH = "scout.png"
X, Y, W, H = 20, 92, 107, 33


def get_elixir():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"Khong tim thay anh: {IMAGE_PATH}")
        return None
    value = read_number(img[Y:Y + H, X:X + W])
    if value is None:
        print("Khong doc duoc Elixir.")
        return None
    print(f"Elixir: {value:,}")
    return value


if __name__ == "__main__":
    get_elixir()
