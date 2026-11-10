import cv2

from COCbot.vision.read_text.numbers import read_number

IMAGE_PATH = "scout.png"
X, Y, W, H = 21, 65, 102, 29


def get_gold_strict():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"Khong tim thay anh: {IMAGE_PATH}")
        return None
    value = read_number(img[Y:Y + H, X:X + W])
    if value is None:
        print("Khong doc duoc Gold.")
        return None
    print(f"Gold: {value:,}")
    return value


if __name__ == "__main__":
    get_gold_strict()
