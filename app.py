import streamlit as st
import pandas as pd
import time
import base64
import uuid
import configparser
from pathlib import Path
from datetime import datetime
from PIL import Image
from st_clickable_images import clickable_images

# =====================================================
# CONFIG
# =====================================================
ADMIN_PASSWORD = "Password!"
CLICK_DELAY = 0.3

# =====================================================
# Functions
# =====================================================
def image_to_base64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def build_item_list(cart: dict):
    items = []
    for pid, item in cart.items():
        items.extend([pid] * item["qty"])
    return items

# =====================================================
# Page config
# =====================================================
st.set_page_config(page_title="POS", layout="wide")
st.title("🧾 Simple POS")

# =====================================================
# Load path config
# =====================================================
config = configparser.ConfigParser()
if not Path("path.ini").exists():
    with open("path.ini", "w") as f:
        f.write("[PATH]\nPRODUCT=product.csv\nIMAGE=images\nRECORD=record.csv")

config.read("path.ini")

PRODUCT = Path(config["PATH"]["PRODUCT"])
IMAGE_DIR = Path(config["PATH"]["IMAGE"])
RECORD = Path(config["PATH"]["RECORD"])

IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# Load products
# =====================================================
if not PRODUCT.exists():
    pd.DataFrame(columns=["id", "name", "price", "image_name"]).to_csv(PRODUCT, index=False)

df = pd.read_csv(PRODUCT, dtype={"id": str})

# =====================================================
# Init record
# =====================================================
if not RECORD.exists():
    pd.DataFrame(columns=["date", "datetime", "items", "total"]).to_csv(RECORD, index=False)

# =====================================================
# Session state
# =====================================================
if "cart" not in st.session_state:
    st.session_state.cart = {}

if "last_click_time" not in st.session_state:
    st.session_state.last_click_time = 0.0

if "gallery_key" not in st.session_state:
    st.session_state.gallery_key = 0

# =====================================================
# 🛍 PRODUCTS
# =====================================================
st.header("🛍 Products")

images, product_ids, titles = [], [], []

for _, row in df.iterrows():
    if pd.notna(row["image_name"]) and row["image_name"]:
        img_path = IMAGE_DIR / row["image_name"]
        if img_path.exists():
            images.append(
                f"data:image/png;base64,{image_to_base64(img_path)}"
            )
            product_ids.append(row["id"])
            titles.append(f"{row['name']} ({row['price']} ฿)")

clicked = clickable_images(
    images,
    titles=titles,
    div_style={"display": "flex", "flex-wrap": "wrap"},
    img_style={
        "margin": "10px",
        "height": "150px",
        "cursor": "pointer",
        "border-radius": "10px"
    },
    key=f"gallery_{st.session_state.gallery_key}" 
)

# -----------------------------------------------------
# Handle image click
# -----------------------------------------------------
if clicked > -1:
    pid = product_ids[clicked]
    product = df[df["id"] == pid].iloc[0]

    # เพิ่มสินค้าลงตะกร้า
    if pid not in st.session_state.cart:
        st.session_state.cart[pid] = {
            "name": product["name"],
            "price": float(product["price"]),
            "qty": 1
        }
    else:
        st.session_state.cart[pid]["qty"] += 1

    st.toast(f"➕ {product['name']} added")

    st.session_state.gallery_key += 1 
    st.session_state.last_click_time = time.time()
    
    st.rerun()

# =====================================================
# 🛒 CART
# =====================================================
st.divider()
st.header("🛒 Cart")

total = 0.0

if not st.session_state.cart:
    st.info("Cart is empty")
else:
    for item in st.session_state.cart.values():
        line = item["price"] * item["qty"]
        total += line
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.write(item["name"])
        c2.write(f"x {item['qty']}")
        c3.write(f"{line:.2f} ฿")

    st.subheader(f"💰 Total: {total:.2f} ฿")

    colA, colB = st.columns(2)

    # ----------------------------
    # Clear cart
    # ----------------------------
    with colA:
        if st.button("🗑 Clear cart"):
            st.session_state.cart = {}
            st.session_state.last_click_time = time.time()
            st.session_state.gallery_key += 1
            st.rerun()

    # ----------------------------
    # Checkout
    # ----------------------------
    with colB:
        if st.button("💾 Checkout"):
            now = datetime.now()
            new_row = {
                "date": now.date().isoformat(),
                "datetime": now.strftime("%H:%M:%S"),
                "items": ",".join(build_item_list(st.session_state.cart)),
                "total": round(total, 2)
            }

            record_df = pd.read_csv(RECORD)
            record_df = pd.concat([record_df, pd.DataFrame([new_row])], ignore_index=True)
            record_df.to_csv(RECORD, index=False)

            st.session_state.cart = {}
            st.session_state.last_click_time = time.time()
            st.session_state.gallery_key += 1
            
            st.success("✅ Checkout completed")
            st.rerun()
            

# =====================================================
# ➕ ADD PRODUCT (ADMIN)
# =====================================================
st.divider()
pwd = st.text_input("Admin password", type="password")

if pwd == ADMIN_PASSWORD:
    with st.expander("➕ Add Product"):
        with st.form("add_product"):
            name = st.text_input("Product name")
            price = st.number_input("Price", min_value=0.0)
            image_file = st.file_uploader("Image", type=["jpg", "png", "jpeg"])
            submit = st.form_submit_button("Add")

            if submit:
                pid = str(uuid.uuid4())[:8]
                image_name = ""

                if image_file:
                    image_name = f"{pid}.png"
                    Image.open(image_file).save(IMAGE_DIR / image_name)

                new_row = {
                    "id": pid,
                    "name": name,
                    "price": price,
                    "image_name": image_name
                }

                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PRODUCT, index=False)

                st.success("✅ Product added")
                st.session_state.gallery_key += 1 
                st.rerun()