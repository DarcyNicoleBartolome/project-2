import customtkinter as ctk
from CTkColorPicker import *

def ask_color():
    pick_color = AskColor() # open the color picker
    color = pick_color.get() # get the color string
    button.configure(fg_color=color)
    
root = ctk.CTk()

button = ctk.CTkButton(master=root, text="CHOOSE COLOR", text_color="black", command=ask_color)
button.pack(padx=30, pady=20)
root.mainloop()