import qrcode

url = "https://fsba-4.onrender.com/"   # put your URL here

qr = qrcode.make(url)
qr.save("qrcode.png")

print("QR code generated as qrcode.png")
