import tkinter
import requests
from tkinter import *

def button_click(button):
    global count, button_swap, layout, buttons

    swap_button = buttons[int(button)-1]

    count += 1

    if (count % 2 == 0):

        swap = button_swap[0]

        swap_button2 = buttons[int(swap)-1]

        x_pos = swap_button2.winfo_rootx()
        y_pos = swap_button2.winfo_rooty()

        swap_button.place(x=x_pos-300, y=y_pos-122)

        x_pos2 = swap_button.winfo_rootx()
        y_pos2 = swap_button.winfo_rooty()

        swap_button2.place(x=x_pos2-300, y=y_pos2-122)

        button_swap[0] = 0
        swap_button2['highlightbackground'] = 'black'


        index = 0
        for i in range(len(layout)):
            if (layout[i] == int(button)):
                button = index
            elif (layout[i] == int(swap)):
                swap = index
            index += 1

        button = int(button)
        swap = int(swap)
        temp = layout[button]
        layout[button] = layout[swap]
        layout[swap] = temp

    else:

        button_swap[0] = button
        swap_button['highlightbackground'] = 'grey'



def on_click_release(event):
    global link_status

    item = canvas.find_closest(event.x, event.y)
    item_type = canvas.type(item)

    if (item_type == 'line'):
        color = canvas.itemcget(item, 'fill')
        link_index = canvas.itemcget(item, 'tags')
        index = ''
        for i in range(len(link_index)):
            if (link_index[i].isdigit()):
                index+= link_index[i]

        if (color == 'green'):
            canvas.itemconfig(item, fill='red')

        elif (color == 'red'):
            canvas.itemconfig(item, fill='green')


def reset():
    global link_status

    requests.get("http://sdn-controller.local:8080/reset_topology")

    for i in range(len(link_status)):
        link_status[i] = True

    update()


def save():
    global link_status, links

    index = 0
    for link in links:

        color = canvas.itemcget(link, 'fill')

        if (color == 'green'):
            link_status[index] = True
        else:
            link_status[index] = False

        index += 1

    connected = []
    index = 0
    for connect in link_status:
        if (connect == True):
            connected.append(index)
            print(index)
        index += 1

    rewrite = []

    for connect in connected:

        pos = connections[connect]
        source = (pos[0])
        dest = (pos[1])

        rewrite.append([source, dest])
        rewrite.append([dest, source])

    requests.put('http://sdn-controller.local:8080/configlinks', json={
        "connected": rewrite
    })


def update():
    global link_status, links

    count = 0
    for i in link_status:
        link = links[count]
        if (i == True):
            canvas.itemconfig(link, fill='green')
        else:
            canvas.itemconfig(link, fill='red')
        count += 1


def load():
    global link_status, connections

    for i in range(len(link_status)):
        link_status[i] = False

    response = requests.get("http://sdn-controller.local:8080/get_topology")

    json_response = response.json()

    for i in json_response['connected']:

        source = str(i[0])
        dest = str(i[1])

        count = 0
        for i in connections:
            if (("[" + source + ", " + dest + "]") == str(i)):
                link_status[count] = True
            count += 1
    update()


def exit():
    pi_gui.destroy()


pi_gui = tkinter.Tk()

pi_gui.title("Raspberry Pi Network")
pi_gui.geometry("680x630+300+100")
pi_gui.configure(bg='gray')

canvas = Canvas(pi_gui, width=700, height=600)
canvas.pack(expand='yes', fill='both')

pi_pic = PhotoImage(file="pi.png")

#left_side = canvas.create_rectangle(0,550, 680, 630, fill='#c19a6b')

# ---------------------Row 1---------------------
button1 = Button(compound=RIGHT, image=pi_pic, text='1', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("1"))
button1.place(x=80, y=10)

button5 = Button(compound=RIGHT, image=pi_pic, text='5', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("5"))
button5.place(x=290, y=10)

button9 = Button(compound=RIGHT, image=pi_pic, text='9', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("9"))
button9.place(x=500, y=10)

link1 = canvas.create_line(165, 50, 290, 50, fill="red", width=5, tags='0')
link2 = canvas.create_line(300, 50, 500, 50, fill="red", width=5, tags='1')


# ----------Links connecting rows 1-2-----------
link9 = canvas.create_line(130, 85, 130, 165, fill="red", width=5, tags='8')
link10 = canvas.create_line(340, 85, 340, 165, fill="red", width=5, tags='9')
link11 = canvas.create_line(550, 85, 550, 165, fill="red", width=5, tags='10')


# ---------------------Row 2---------------------
button2 = Button(compound=RIGHT, image=pi_pic, text='2', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("2"))
button2.place(x=80, y=160)

button6 = Button(compound=RIGHT, image=pi_pic, text='6', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("6"))
button6.place(x=290, y=160)

button10 = Button(compound=RIGHT, image=pi_pic, text='10', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("10"))
button10.place(x=500, y=160)

link3 = canvas.create_line(165, 200, 290, 200, fill="red", width=5, tags='2')
link4 = canvas.create_line(300, 200, 500, 200, fill="red", width=5, tags='3')


# ----------Links connecting rows 2-3-----------
link12 = canvas.create_line(130, 235, 130, 315, fill="red", width=5, tags='11')
link13 = canvas.create_line(340, 235, 340, 315, fill="red", width=5, tags='12')
link14 = canvas.create_line(550, 235, 550, 315, fill="red", width=5, tags='13')


# ---------------------Row 3---------------------
button3 = Button(compound=RIGHT, image=pi_pic, text='3', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 20), command=lambda: button_click("3"))
button3.place(x=80, y=310)

button7 = Button(compound=RIGHT, image=pi_pic, text='7', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 17), command=lambda: button_click("7"))
button7.place(x=290, y=310)

button11 = Button(compound=RIGHT, image=pi_pic, text='11', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 17), command=lambda: button_click("11"))
button11.place(x=500, y=310)

link5 = canvas.create_line(165, 350, 290, 350, fill="red", width=5, tags='4')
link6 = canvas.create_line(300, 350, 500, 350, fill="red", width=5, tags='5')


# ----------Links connecting rows 3-4-----------
link15 = canvas.create_line(130, 385, 130, 465, fill="red", width=5, tags='14')
link16 = canvas.create_line(340, 385, 340, 465, fill="red", width=5, tags='15')
link17 = canvas.create_line(550, 385, 550, 465, fill="red", width=5, tags='16')


# ---------------------Row 4---------------------
button4 = Button(compound=RIGHT, image=pi_pic, text='4', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 17), command=lambda: button_click("4"))
button4.place(x=80, y=460)

button8 = Button(compound=RIGHT, image=pi_pic, text='8', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 17), command=lambda: button_click("8"))
button8.place(x=290, y=460)

button12 = Button(compound=RIGHT, image=pi_pic, text='12', foreground='white', highlightbackground='black',
                 font=('Times New Roman', 17), command=lambda: button_click("12"))
button12.place(x=500, y=460)

link7 = canvas.create_line(165, 500, 290, 500, fill="red", width=5, tags='6')
link8 = canvas.create_line(300, 500, 500, 500, fill="red", width=5, tags='7')


#--------------------Bottom---------------------
reset_pic = PhotoImage(file="reset.png")

box1 = canvas.create_rectangle(190, 570, 480, 625, outline='grey', fill='green', width='4')

exit_button = Button(text='EXIT', foreground='white', highlightbackground='black', font=('Times New Roman', 25), command=exit)
exit_button.place(x=307, y=580)

save_button = Button(text='SAVE', foreground='white', highlightbackground='black', font=('Times New Roman', 25), command=save)
save_button.place(x=400, y=580)

load_button = Button(text='LOAD', foreground='white', highlightbackground='black', font=('Times New Roman', 25), command=load)
load_button.place(x=200, y=580)

reset_button = Button(compound=BOTTOM, image=reset_pic, text='RESET', foreground='black', font=('Times New Roman', 16), command=reset)
reset_button.place(x=620, y=560)

canvas.bind('<ButtonRelease-1>', on_click_release)


button_swap = [0]
count = 0

buttons = [button1, button2, button3, button4, button5, button6, button7, button8, button9, button10, button11, button12]

layout = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

connections = [[1,2], [2,3], [3,4], [5,6], [6,7], [7,8], [9,10], [10,11], [11,12], [1,5], [5,9], [2,6], [6,10], [3,7], [7,11], [4,8], [8,12]]

link_status = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]

links = [link9, link12, link15, link10, link13, link16, link11, link14, link17, link1, link2, link3, link4, link5, link6, link7, link8]

pi_gui.mainloop()
