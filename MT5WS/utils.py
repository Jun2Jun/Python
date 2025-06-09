from PIL import ImageTk
import pyautogui

# スクリーンショットの取得
def take_full_screenshot():
    return pyautogui.screenshot()

# イメージから任意のエリアの切り出し
def get_cropped_screenshot_from_image(full_img, x, y, width, height):
    crop = full_img.crop((x, y, x + width, y + height))
    return ImageTk.PhotoImage(crop)