
import tkinter as tk
import tkinter.font as font
from tkinter import filedialog as fd
from tkinter import ttk
import tkinter.messagebox as tmb
import Wave as TI_wave
import os
from cas2b74 import TI75_Basic
from cas2b74 import ERROR_MSG
import datetime
import time
import serial

import serial.tools.list_ports
import platform

FILA_0 = 0
FILA_1 = 0
FILA_2 = 1
FILA_3 = 2
FILA_4 = 3

WAVE_DATA, CASSETTE_DATA, CBASIC_DATA, BASIC_DATA = range (4)
PROGRAM_NAME = "TI-74 Software Management"
file_name = None

class Espere_Window_Obj (tk.Toplevel):
    def __init__ (self, titulo, texto1, texto2, icono, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(titulo)
        self.geometry('350x160+700+400')
        self.resizable(False, False)
        self.container = tk.Frame(self)
        self.container.pack()
        self.imagen_WAIT = tk.PhotoImage(file=icono)
        tk.Label(self.container, text=texto1).pack(padx="10 10", pady="10 5", side=tk.TOP, fill=tk.X)
        tk.Label(self.container, image=self.imagen_WAIT).pack(padx="10 10", pady="10 5", side=tk.TOP, fill=tk.X)
        tk.Label(self.container, text=texto2).pack(padx="10 10", pady="10 5", side=tk.TOP, fill=tk.X)


class REC_Window_Obj (tk.Toplevel):
    def __init__(self, wave, arduino, REC_arduino='False', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.REC_arduino = REC_arduino
        if self.REC_arduino:
            self.arduino=arduino
            self.imagen_START = tk.PhotoImage(file='icons/START_06.gif')
            self.title('REC-Arduino from TI-74')
        else:
            self.wave = wave
            self.imagen_START = tk.PhotoImage(file='icons/START_07.gif')
            self.wave.set_recording(True)
            self.title('REC-MIC from TI-74')
        self.geometry('350x240+700+400')

        self.resizable(False, False)
        # Buttons definition
        tk.Label(self, text='Introduce the SAVE commands in the TI-74\n\n SAVE "1.FILE_NAME"\n\nand follow TI-74 instructions. Press botton to start recording...').pack(padx="10 10", pady="10 5", side=tk.TOP)
        start_button = tk.Button(self, text="START RECORD", image=self.imagen_START,  compound = tk.BOTTOM, command = self.iniciar_REC)
        start_button.photo = self.imagen_START # This sentence is required because it is in a Toplevel window and the PhotImage has a bug...    
        start_button.pack(ipadx=20, ipady=10, pady="5 10", side=tk.TOP)
        comentario = tk.Label(self, text='Once recording starts, this window will close automatically...')
        comentario.pack()
        # self.protocol('WM_DELETE_WINDOW', self.close_REC_window)

    def iniciar_REC (self): 
        if self.REC_arduino:
            self.arduino.Read_Arduino()
        else:
            # Initialize the Recording settings
            self.wave.set_default()
            # Start recording...
            self.wave.record_data()
            # to enable the main window
            self.wave.set_recording(False)
        self.event_generate('<<CloseREC>>', when='tail')
      

class EDIT_Window_Obj (tk.Toplevel):
    def __init__(self, name, basic_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.basic = basic_text
        self.name = name
        self.title(self.name)
        self.geometry('450x540+300+200')
        self.resizable(True, True)
        self.cancel_edit = True
        
        # Shortcut Bar.
        self.shortcut_bar = tk.Frame(self,  height=25)
        self.shortcut_bar.pack(expand='no', fill='x')
        icons = ('Clear_file', 'Cut', 'Copy', 'Paste',
                 'Undo', 'Redo', 'Find_text')
        for i, icon in enumerate(icons):
            self.tool_bar_icon = tk.PhotoImage(file='icons/{}.gif'.format(icon))
            self.cmd = eval('self.'+icon)
            self.tool_bar = tk.Button(self.shortcut_bar, image=self.tool_bar_icon, command=self.cmd)
            self.tool_bar.image = self.tool_bar_icon
            self.tool_bar.pack(side='left', padx=1)
        self.exit_edit = tk.Button(self.shortcut_bar, text='EXIT EDIT', bg='cyan', command=self.Exit_Edit)
        self.exit_edit['font']=font.Font(weight='bold', size=10)
        self.exit_edit.pack(side='left', padx='25 25', pady='1 1')
        self.cancel_edit = tk.Button(self.shortcut_bar, text='CANCEL EDIT', bg='red', fg='yellow', command=self.Cancel_Edit)
        self.cancel_edit['font']=font.Font(weight='bold', size=10)
        self.cancel_edit.pack(side='right', padx=5, pady='1 1')

        
        # The BASIC text editor itself, for a stetic, inside of a frame.
        self.text_frame = tk.Frame (self, borderwidth=2, relief="sunken")
        self.text_frame.pack(expand=True, fill='both')
        self.content_text = tk.Text(self.text_frame, wrap='none', undo=True)
        # pack the text widget before the scroll bars, otherwise the scrollbars will hide characters...
        
        # Vertical scroll bar.
        self.vert_scroll_bar = tk.Scrollbar(self.text_frame, orient='vertical')
        self.content_text.configure(yscrollcommand=self.vert_scroll_bar.set)
        self.vert_scroll_bar.config(command=self.content_text.yview)
        self.vert_scroll_bar.pack(side='right', fill='y')
        # Horiziontal scroll bar.
        self.hor_scroll_bar = tk.Scrollbar(self.text_frame, orient='horizontal')
        self.content_text.configure(xscrollcommand=self.hor_scroll_bar.set)
        self.hor_scroll_bar.config(command=self.content_text.xview)
        self.hor_scroll_bar.pack(side='bottom', fill='x')

        # Finally pack the text widget.
        self.content_text.pack(side='left',expand='yes', fill='both')
        
        # Binding special keys
        self.content_text.bind('<Control-N>', self.Clear_file)
        self.content_text.bind('<Control-n>', self.Clear_file)
        self.content_text.bind('<Control-f>', self.Find_text) 
        self.content_text.bind('<Control-F>', self.Find_text)
        self.content_text.bind('<Control-A>', self.Select_all)
        self.content_text.bind('<Control-a>', self.Select_all)
        self.content_text.bind('<Control-y>', self.Redo)
        self.content_text.bind('<Control-Y>', self.Redo)
        # Delete the existing content.
        self.content_text.delete(1.0, tk.END)
        # Insert the BASIC code lines
        for text in self.basic:
            self.content_text.insert(tk.END, text+'\n')
        # Inicialize the modifier and reset UNDO 
 
        self.content_text.edit_modified(False)
        self.content_text.edit_reset()
        # Get the focus
        self.content_text.focus_set()
        # Positioning the cursor at the text start.
        self.content_text.mark_set("insert", "{:d}.{:d}".format(1, 0))

    def Clear_file(self, event=None):
        #selfroot.title("Untitled")
        #global file_name
        #file_name = None
        self.content_text.delete(1.0, tk.END)
        #on_content_changed()

    def Select_all(self, event=None):
        self.content_text.tag_add('sel', '1.0', 'end')
        return "break"

    def Cut(self):
        self.content_text.event_generate("<<Cut>>")
        #on_content_changed()
        return "break"

    def Copy(self):
        self.content_text.event_generate("<<Copy>>")
        return "break"

    def Paste(self):
        self.content_text.event_generate("<<Paste>>")
        #on_content_changed()
        return "break"

    def Undo(self):
        self.content_text.event_generate("<<Undo>>")
        #on_content_changed()
        return "break"

    def Redo(self, event=None):
        self.content_text.event_generate("<<Redo>>")
        #on_content_changed()
        return 'break'

    def Find_text(self, event=None):
        search_toplevel = tk.Toplevel(self)
        search_toplevel.title('Find Text')
        search_toplevel.transient(self)

        tk.Label(search_toplevel, text="Find All:").grid(row=0, column=0, sticky='e')

        search_entry_widget = tk.Entry(
            search_toplevel, width=25)
        search_entry_widget.grid(row=0, column=1, padx=2, pady=2, sticky='we')
        search_entry_widget.focus_set()
        ignore_case_value = tk.IntVar()
        tk.Checkbutton(search_toplevel, text='Ignore Case', variable=ignore_case_value).grid(
            row=1, column=1, sticky='e', padx=2, pady=2)
        tk.Button(search_toplevel, text="Find All", underline=0,
            command=lambda: self.search_output(
                search_entry_widget.get(), ignore_case_value.get(),
                self.content_text, search_toplevel, search_entry_widget)
            ).grid(row=0, column=2, sticky='e' + 'w', padx=2, pady=2)

        def close_search_window():
            self.content_text.tag_remove('match', '1.0', tk.END)
            search_toplevel.destroy()

        search_toplevel.protocol('WM_DELETE_WINDOW', close_search_window)
        return "break"

    def search_output(self, needle, if_ignore_case, content_text,
                    search_toplevel, search_box):
        self.content_text.tag_remove('match', '1.0', tk.END)
        matches_found = 0
        if needle:
            start_pos = '1.0'
            while True:
                start_pos = content_text.search(needle, start_pos,
                                                nocase=if_ignore_case, stopindex=tk.END)
                if not start_pos:
                    break
                end_pos = '{}+{}c'.format(start_pos, len(needle))
                content_text.tag_add('match', start_pos, end_pos)
                matches_found += 1
                start_pos = end_pos
            content_text.tag_config(
                'match', foreground='red', background='yellow')
        search_box.focus_set()
        search_toplevel.title('{} matches found'.format(matches_found))

    def Exit_Edit (self):
        self.cancel_edit = False
        self.destroy()

    def Cancel_Edit (self):
        self.destroy()


class Options_Window_Obj (tk.Toplevel):
    def __init__(self, input_lista, output_lista, log_option, arduino_opt, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('TI-74: OPTIONS')
        self.geometry('350x250+700+400')
        self.resizable(False, False)
        self.cancel_options = True

        # Buttons definition
        # label
        self.label = ttk.Label(self, text="Please select a INPUT device:")
        self.label.pack(fill=tk.X, padx=5, pady=5)

        # create a combobox
        self.selected_input = tk.StringVar()
        self.input_cb = ttk.Combobox(self, textvariable=self.selected_input)
        # prevent typing a value
        self.input_cb['state'] = 'readonly'
        # place the widget
        self.input_cb.pack(fill=tk.X, padx=5, pady=5)

        # label
        self.label = ttk.Label(self, text="Please select an OUTPUT device:")
        self.label.pack(fill=tk.X, padx=5, pady="20 5")

        # create a combobox
        self.selected_output = tk.StringVar()
        self.output_cb = ttk.Combobox(self, textvariable=self.selected_output)
        # prevent typing a value
        self.output_cb['state'] = 'readonly'
        # place the widget
        self.output_cb.pack(fill=tk.X, padx=5, pady=5)

        # Arduino a CheckBox button 
        self.arduino_opt = tk.IntVar()
        self.arduino_opt.set(arduino_opt.get())
        self.create_arduino = tk.Checkbutton (self, text='Use Arduino LEONARDO if connected.', variable=self.arduino_opt, onvalue=1, offvalue=0)
        self.create_arduino.pack(fill = tk.BOTH, padx = '110 5', pady=5)

        # Conversion Log file a CheckBox button 
        self.log_file = tk.IntVar()
        self.log_file.set(log_option.get())
        self.create_log = tk.Checkbutton (self, text='Create a conversion log file.', variable=self.log_file, onvalue=1, offvalue=0)
        self.create_log.pack(fill = tk.BOTH, padx = '170 5', pady=5)

        # Accept button
        self.OK_boton = tk.Button(self, text='ACCEPT CHANGES', command=self.OK_Exit)
        self.OK_boton['font']=font.Font(weight='bold', size=10)
        self.OK_boton.pack (side=tk.LEFT, padx=10, pady=10)
        # Cancel button
        self.cancel_boton = tk.Button(self, text='CANCEL CHANGES', bg='red', fg='yellow', command=self.CANCEL_Exit)
        self.cancel_boton['font']=font.Font(weight='bold', size=10)
        self.cancel_boton.pack (side=tk.RIGHT, padx=10, pady=10)

    def OK_Exit(self):
        self.cancel_options = False
        self.event_generate('<<CloseSettings>>', when='tail')

    def CANCEL_Exit (self):
        self.event_generate('<<CloseSettings>>', when='tail')


class Arduino ():
    def __init__(self):
        self.ba = b''
        self.port = None
        self.Find_Arduino()
        self.dataread = 0

    def Find_Arduino(self):
        portList = list(serial.tools.list_ports.comports())
        for port in portList:
            if "VID:PID=2341:8036" in port[0]\
                or "VID:PID=2341:8036" in port[1]\
                or "VID:PID=2341:8036" in port[2]:
                self.port = port[0]

    def get_Arduino_port(self):
        return self.port

    def get_data(self):
        return self.ba

    def set_data(self, data):
        self.ba = data
        return

    def Read_Arduino(self):
        try:
            arduinoPort = serial.Serial(self.port, 9600, timeout=15)
            # Retardo para establecer la conexión serial
            time.sleep(3)
            # Reset manual del Arduino
            arduinoPort.setDTR(False)  
            time.sleep(0.3)  
            # Se borra cualquier data que haya quedado en el buffer
            arduinoPort.flushInput()  
            arduinoPort.setDTR()
        except:
            tmb.showerror ('Communication ERROR', 'ERROR: {} - {}'.format(102, ERROR_MSG[102]))
            return
        time.sleep(0.3)
        self.dataread=0
        self.ba=b''
        with arduinoPort:
            element=arduinoPort.read()
            while len(element) > 0:
                self.ba += element
                self.dataread += 1
                element=arduinoPort.read()
        # To add an 0xff to end for the integrity of the overall data.
        self.ba += 0xff.to_bytes(1,'little')
        # Closing serial port...
        arduinoPort.close()
        
        return

    def Write_Arduino(self):
        try:
            arduinoPort = serial.Serial(self.port, 9600, timeout=5)
            # Retardo para establecer la conexión serial
            time.sleep(3)
            # Reset manual del Arduino
            arduinoPort.setDTR(False)  
            time.sleep(0.3)  
            # Se borra cualquier data que haya quedado en el buffer
            arduinoPort.flushInput()  
            arduinoPort.setDTR()  
        except:
            tmb.showerror ('Communication ERROR', 'ERROR: {} - {}'.format(102, ERROR_MSG[102]))
            return
        time.sleep(0.3)
        Numero=0
        with arduinoPort:
            #tic2=time.time()
            for i in range(len(self.ba)):
                Elemento=arduinoPort.write(self.ba[i].to_bytes(1,'little'))
                Numero += 1
        # Cerrando puerto serial
        arduinoPort.close()



class Principal (tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master=master
        self.pack()
        self.master.title(PROGRAM_NAME) # Título de la ventana.
        self.master.resizable(False, False)
        self.name = 'prueba'
        # Create the baisc objes for the TI-74
        self.wave = TI_wave.TI75_AudioFile(self.name) # The name of the file is does not matter now, later can be changed
        self.basic= TI75_Basic(name=self.name)
        self.arduino = Arduino()
        # Search the ARDUINO LEONARDO board
        self.arduino_port = self.arduino.get_Arduino_port()
        # Create the widgets
        self.available_data = [0]*4 # No data available
        self.arduino_option = tk.IntVar()
        self.arduino_option.set(1)
        self.log_option = tk.IntVar()        
        self.log_option.set(0)
        self.save_log = False
        self.log_file = None
        self.Create_widgets()
         # Redirect the destroy event
        self.master.protocol ("WM_DELETE_WINDOW", self.Close_app) 
        self.Init_data()

    def Convert_data (self, target, direction = 0):
        ''' Conversion de DATA
        INPUT: 
            - target: final data conversion: WAVE_DATA, CASSETTE_DATA, CBASIC_DATA or BASIC_DATA
            - direction: three options (do not use in the main program, it is for the recursivity process only):
                -1: direction: BASIC --> CBASIC --> CASSETTE --> WAV
                 0: to be defined de best direction.
                +1: direction: WAV --> CASSETTE --> CBASIC --> BASIC
            '''
        if 1 in self.available_data:
            Error=0 
            if direction == 0: # Analysis of conversion direction (sense)
                # Build & show a conversion waiting window.....
                self.ventana_convert = Espere_Window_Obj(titulo ='TI-74: Data conversion', texto1='Converting DATA, please wait until the process ends.', \
                                    texto2='This window will close automatically...',icono='icons/conversion.gif')
                self.ventana_convert.overrideredirect(1) # no window decoration
                #self.ventana.transient(self) # dialog window is related to main
                self.ventana_convert.wait_visibility() # can't grab until window appears, so we wait
                self.ventana_convert.grab_set() #The grab_set() method prevents users from interacting with the main window.
                self.ventana_convert.update_idletasks()
                if target == 0: # Target: WAVE file data
                    direction = -1
                elif target == 1: # Target: CASSETTE file data
                    if self.available_data[WAVE_DATA] == 1:
                        direction = +1
                    else:
                        direction = -1
                elif target == 2: # Target: COMPRESSED BASIC CODE file data
                    if self.available_data[BASIC_DATA] == 1:
                        direction = -1
                    else: # Target: TEXT BASIC CODE file data
                        direction = +1
                else:
                    direction = +1
                Error = self.Convert_data(target, direction)
                self.ventana_convert.destroy() # Destroy the waiting window.
                return Error
            else:
                while self.available_data[target-direction] != 1:
                    Error = self.Convert_data(target-direction, direction)
                    if Error !=0:
                        return Error
            if target == 0: # Target: WAVE file data
                self.wave.cassette_section_to_wave(self.save_log, self.log_file)
                self.available_data[WAVE_DATA] = 1
            elif target == 1: # Target: CASSETTE file data
                if direction == +1:
                    Error = self.wave.wav_to_cassette_section(self.save_log, self.log_file)
                    self.basic.set_cassette_section(self.wave.get_cassette_section())
                else:
                    new_name = self.basic.cbasic_to_cassette_section(self.save_log, self.log_file)
                    if new_name != self.name:
                        tmb.showinfo ("CASSETTE NAME", 'Cassette name changed to: {}'.format(new_name))
                    self.wave.set_cassette_section(self.basic.get_cassette_section())
                self.available_data[CASSETTE_DATA] = 1
            elif target == 2: # Target: COMPRESSED BASIC CODE file data
                if direction == +1:
                    #self.basic.set_cassette_section(self.wave.get_cassette_section())
                    Error, name = self.basic.cassette_section_to_cbasic(self.save_log, self.log_file)
                    if Error == 0:
                        self.name = name
                        self.wave.set_filename (self.path, self.name)
                        self.basic.set_filename (self.path, self.name, self.extension)
                else:
                    self.basic.basic_to_cbasic(self.save_log, self.log_file)
                self.available_data[CBASIC_DATA] = 1
            else: # Target: TEXT BASIC CODE file data
                self.basic.cbasic_to_basic(self.save_log, self.log_file)
                self.available_data[BASIC_DATA] = 1
            return Error            
        else:
            tmb.showerror ('No DATA', 'LOAD or CREATE a new data file first')
            return 100

    def Init_data (self, wave = 0, cassette=0, cbasic=0, basic=0, name='', extension='',  path=''):
        self.available_data[WAVE_DATA] = wave
        self.available_data[CASSETTE_DATA] = cassette
        self.available_data[CBASIC_DATA] = cbasic
        self.available_data[BASIC_DATA] = basic
        if name == '':
            self.name = 'prueba'
        else:
            self.name = name
        self.extension = extension
        if path == '':
            self.path = '.'
        else:
            self.path = path
        self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))

    def Create_widgets(self):
        # WAVE FRAME
        self.frame_wave = tk.Frame (self, highlightthickness=2 ,borderwidth=2, relief='ridge')
        self.frame_wave.grid(row=0, column=0, padx="5 5", pady="30 10", sticky="n")
        # Buttons definition
        self.img_REC = tk.PhotoImage(file='icons/REC.gif')
        self.img_opciones = tk.PhotoImage(file='icons/Settings32.gif')
        self.boton_rec = tk.Button (self.frame_wave, text='REC', image=self.img_REC, compound = tk.LEFT, command=self.Open_REC_Window)
        self.boton_open_wave = tk.Button (self.frame_wave, text='Open WAVE', command=self.Open_Wave_File_Name)
        # Option button
        self.boton_opciones = tk.Button (self, image=self.img_opciones, command=self.Open_Settings) 
        self.boton_opciones.grid (row=1, column=0, padx="2 5", pady="5 5", sticky='SW')
        # Localize the REC & Open buttons.
        self.boton_rec.pack (padx="5 5", pady="5 5", side=tk.TOP, fill=tk.X)
        self.boton_open_wave.pack (padx="5 5", pady="5 5", side=tk.BOTTOM, fill=tk.X)

        # CENTRAL FRAME
        self.frame_central = tk.Frame (self, highlightthickness=2 ,borderwidth=2, relief='ridge')
        self.frame_central.grid(row=0, column=1, rowspan=2, padx="5 5", pady="5 5", sticky="nsew")
        # Images definition
        self.img_central = tk.PhotoImage(file='icons/TI-74-peque.gif')
        self.central = tk.Label (self.frame_central, image=self.img_central)
        self.central.grid(row=0, column=0, columnspan=3, rowspan=3)

        # Buttons definition
        self.img_PLAY = tk.PhotoImage(file='icons/PLAY.gif')
        self.boton_play = tk.Button (self.frame_central, text='PLAY', image=self.img_PLAY, compound = tk.LEFT, command = self.Play_wave)
        self.boton_save_wave = tk.Button (self.frame_central, text='Save WAVE', command=self.Save_Wave_File_Name)
        #self.boton_new = tk.Button (self.frame_central, text='NEW', width=10)
        self.boton_edit = tk.Button (self.frame_central, text='Edit BASIC', command=self.Open_EDIT_Window)
        self.boton_save_basic = tk.Button (self.frame_central, text='Save BASIC', command=self.Save_BASIC_File_Name)
        # Localize the buttons
        self.boton_play.grid (row=FILA_1, column=0, padx="10 10", pady="55 40", sticky="ew")
        self.boton_save_wave.grid (row=FILA_3, column=0, padx="10 10", pady="30 55", sticky="ew")
        #self.boton_new.grid (row=FILA_2, column=1, padx="10 10", pady="10 10", sticky="ew")
        self.boton_save_basic.grid (row=FILA_1, column=2, padx="10 10", pady="55 40", sticky="ew")
        self.boton_edit.grid (row=FILA_3, column=2, padx="10 10", pady="30 55", sticky="ew")                          
                                
        # BASIC FRAME
        if self.arduino_port:
            self.arduino_on = tk.PhotoImage(file='icons/Arduino_On.gif')
            self.arduino_off = tk.PhotoImage(file='icons/Arduino_Off.gif')
            if self.arduino_option.get() == 0:
                self.arduino_label = tk.Label (self, image=self.arduino_off)
            else:
                self.arduino_label = tk.Label (self, image=self.arduino_on)
            self.arduino_label.grid (row=0, column=2, padx="5 5", pady="3 3", sticky='N')    
            #self.arduino_Labe.photo=self.arduino_off
        self.frame_basic= tk.Frame (self, highlightthickness=2 ,borderwidth=2, relief='ridge')
        self.frame_basic.grid(row=1, column=2, padx="5 5", pady="0 35", sticky="s")
        # Arduino image

        # Buttons definition
        self.boton_open_basic = tk.Button (self.frame_basic, text='Open BASIC', command=self.Open_BASIC_File_Name)
        # Localize the buttons
        self.boton_open_basic.pack (padx="5 5", pady="22 22", side=tk.LEFT, fill=tk.X)    
        
    def Open_REC_Window(self):
        # Crerate a new Object, it is 'self' to get the control from this object
        if self.arduino_port != None and self.arduino_option.get() == 1:
            # REC from ARDUINO
            self.Window_01 = REC_Window_Obj(wave=self.wave, arduino=self.arduino, REC_arduino=True)
        else:
            # REC from audio 
            self.Window_01 = REC_Window_Obj(wave=self.wave, arduino=self.arduino, REC_arduino=False)

        # To save the new BASIC DATA, we need to control its destroy from this object
        self.Window_01.protocol ("WM_DELETE_WINDOW", lambda: self.Keep_REC_data(True))
        self.Window_01.bind('<<CloseREC>>', self.Keep_REC_data)
        self.Window_01.grab_set() #The grab_set() method prevents users from interacting with the main window.

    def Keep_REC_data (self, Event):
        if self.arduino_port != None and self.arduino_option.get() == 1:
            if len(self.arduino.ba)>0:
                self.arduino.ba = self.Window_01.arduino.ba
                if len(self.arduino.ba)>0:
                    if self.log_option.get() == 1:
                        self.log_file.write ('Number of bytes collected from Arduino LEONARDO: {:d}\n\n'.format(self.arduino.dataread))                    
                    self.basic.set_cassette_full(self.arduino.get_data())
                    # self.basic.save_file_cassette_full()
                    Error, name = self.basic.cassette_full_to_cassette_section(self.save_log, self.log_file)
                    if Error != 0:
                        tmb.showerror ('Conversion ERROR', 'ERROR: {} - {}'.format(Error, ERROR_MSG[Error]))
                        self.Init_data() # Reset the initial data
                    else:
                        self.name = name
                        self.wave.set_filename (self.path, self.name)
                        self.basic.set_filename (self.path, self.name, self.extension)
                        self.Init_data (cassette=1, name=self.name, extension='r74', path=self.path)
                        self.master.title('{} - {}'.format(self.name, PROGRAM_NAME)) 
                        self.wave.set_cassette_section(self.basic.get_cassette_section())
            else:
                tmb.showerror ('Read ERROR', 'ERROR: {} - {}'.format(101, ERROR_MSG[101]))
        else:
            self.Window_01.wave.stop_REC()
            self.Window_01.wave.set_recording(False) 
            # Keep the recorded data        
            self.wave.playable = self.Window_01.wave.set_playable
            if self.wave.playable:
                self.wave.data_all = self.Window_01.wave.data_all
                # Initilize all data.
                self.Init_data (wave=1, name=self.name, extension='wav', path=self.path)
        # to enable the main window
        self.Window_01.unbind('<<CloseREC>>')
        self.Window_01.destroy()

    def Open_Wave_File_Name (self):
        self.input_file_name = fd.askopenfilename(defaultextension=".wav",
                                            filetypes=[("Wave files", "*.wav"), ("Binary wave files", "*.r74"), ("All Files", "*.*")])
        if self.input_file_name:
            global file_name
            file_name = self.input_file_name
            name = os.path.basename(file_name)
            path = os.path.dirname(file_name)
            auxiliar = name.rsplit('.',1)
            name = auxiliar[0].upper() # Name of the file
            '''
            # To normalize the name
            if self.name[0] in ['0','1','2','3','4','5','6','7','8','9']:
                self.name='A'+self.name
            self.name = self.name.replace (",", "") # Remov3 "," character
            self.name = self.name.replace (".", "") # Remove "." character
            if len(self.name) > 18:
                self.name=self.name[0:18]
            '''
            try: # Extension of the file
                extension = auxiliar[1].lower()
            except:
                extension = ''
            if path =='':
                path = "."
            self.wave.set_playable (False)
            if extension == 'wav': # Read the WAVE file name.
                self.Init_data (wave=1, name=name, extension=extension, path=path)
                self.wave.set_filename (self.path, self.name)
                self.basic.set_filename (self.path, self.name, self.extension)                
                self.wave.read_file() # Read de WAVE file
                self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))
            elif extension == 'r74': # Read the Binary data.
                # Update the FILE information
                self.Init_data (cassette=1, name=name, extension=extension, path=path)
                self.wave.set_filename (self.path, self.name)
                self.basic.set_filename (self.path, self.name, self.extension)
                # Read the CASSETTE file
                self.basic.read_file_cassette_full() # Read de WAVE-BINARY file
                # Convert to CASSETTE_SECTION
                Error, name = self.basic.cassette_full_to_cassette_section(self.save_log, self.log_file)
                if Error != 0:
                    tmb.showerror ('Conversion ERROR', 'ERROR: {} - {}'.format(Error, ERROR_MSG[Error]))
                    self.Init_data() # Reset the initial data
                else:
                    self.wave.set_cassette_section(self.basic.get_cassette_section())
                    self.master.title('{} - {}'.format(self.name, PROGRAM_NAME)) 

    def Save_Wave_File_Name (self):
        # TODO: Verify the name of the file inside the WAVE data.
        if 1 in self.available_data:
            self.input_file_name = fd.asksaveasfilename(defaultextension=".bas", initialfile=self.name,
                                        filetypes=[("Wave file", "*.wav"), ("Raw cassette files", "*.r74"), ("All Files", "*.*")])
            if self.input_file_name:
                global file_name
                file_name = self.input_file_name
                name = os.path.basename(file_name)
                path = os.path.dirname(file_name)
                auxiliar = name.rsplit('.',1)
                name = auxiliar[0].upper() # Name of the file
                try: # Extension of the file
                    extension = auxiliar[1].lower()
                except:
                    extension = ''
                if path =='':
                    path = "."
                if extension not  in ['r74', 'wav']:
                    tmb.showerror ('Wrong EXTENSION', 'Correct EXTENSIONS: \n wav for a WAVE file.\n r74 for raw CASSETTE file')
                elif extension == 'wav':
                    Error = 0
                    if self.available_data[WAVE_DATA] == 0:
                        Error = self.Convert_data(WAVE_DATA)
                    if Error ==0:
                        # Update Name, Extension & Path
                        self.Init_data (wave=self.available_data[WAVE_DATA], cassette=self.available_data[CASSETTE_DATA], \
                                        cbasic=self.available_data[CBASIC_DATA], basic=self.available_data[BASIC_DATA], \
                                        name=name, extension=extension, path=path)
                        self.wave.set_filename(self.path, self.name)
                        self.basic.set_filename (self.path, self.name, self.extension)
                        self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))
                        self.wave.save_data_to_file()
                    else:
                        tmb.showerror("Conversion ERROR', 'ERROR: {} - {}".format(Error, ERROR_MSG[Error]))  #, "Unable to convert from existing DATA to WAVE")
                elif extension == 'r74':
                    Error = 0 
                    if self.available_data[CASSETTE_DATA] == 0:
                        Error = self.Convert_data(CASSETTE_DATA)
                    if Error == 0:
                        # Update Name, Extension & Path
                        self.Init_data (wave=self.available_data[WAVE_DATA], cassette=self.available_data[CASSETTE_DATA], \
                                        cbasic=self.available_data[CBASIC_DATA], basic=self.available_data[BASIC_DATA], \
                                        name=name, extension=extension, path=path)
                        self.wave.set_filename(self.path, self.name)
                        self.basic.set_filename (self.path, self.name, self.extension)
                        self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))
                        self.basic.cassette_section_to_cassette_full()
                        self.basic.save_file_cassette_full()
                    else:
                        tmb.showerror("Conversion ERROR', 'ERROR: {} - {}".format(Error, ERROR_MSG[Error]))  #, "Unable to convert from existing DATA to RAW CASSETTE")
        else:
            tmb.showerror ('No DATA', 'LOAD or CREATE a new file first')

    def Open_BASIC_File_Name (self):
        self.input_file_name = fd.askopenfilename(defaultextension=".bas",
                                            filetypes=[("Basic Text files", "*.bas"), ("Basic Text files", "*.b74"), \
                                                       ("compressed Basic files", "*.c74"), ("All Files", "*.*")])
        if self.input_file_name:
            global file_name
            file_name = self.input_file_name
            name = os.path.basename(file_name)
            path = os.path.dirname(file_name)
            auxiliar = name.rsplit('.',1)
            name = auxiliar[0].upper() # Name of the file
            '''
            # To normalize the name to TI-74 accepted characters.
            if self.name[0] in ['0','1','2','3','4','5','6','7','8','9']:
                self.name='A'+self.name
            self.name = self.name.replace (",", "") # Remove "," character
            self.name = self.name.replace (".", "") # Remove "." character
            if len(self.name) > 18:
                self.name=self.name[0:18]
            '''
            try: # Extension of the file
                extension = auxiliar[1].lower()
            except:
                extension = ''
            if path == '':
                path = "."
            self.wave.set_playable (False)
            if extension == 'bas' or extension == 'b74': 
                self.Init_data (basic=1, name=name, extension=extension, path=path)
                self.wave.set_filename (self.path, self.name)
                self.basic.set_filename (self.path, self.name, self.extension)
                self.basic.read_basic() # Read de BASIC TEXT file
                self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))
            elif extension == 'c74': # Read the COMPRESSED BASIC data.
                self.Init_data (cbasic=1, name=name, extension=extension, path=path)
                self.wave.set_filename (self.path, self.name)
                self.basic.set_filename (self.path, self.name, self.extension)
                self.basic.read_cbasic()
                self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))

    def Save_BASIC_File_Name (self):
        if 1 in self.available_data:
            self.input_file_name = fd.asksaveasfilename(defaultextension=".bas", initialfile=self.name,
                                        filetypes=[("TI-74 Basic Text files", "*.b74"), ("Standard Basic Text files", "*.bas"), \
                                                   ("Compressed Basic files", "*.c74"), ("All Files", "*.*")])
            if self.input_file_name:
                global file_name
                file_name = self.input_file_name
                name = os.path.basename(file_name)
                path = os.path.dirname(file_name)
                auxiliar = name.rsplit('.',1)
                name = auxiliar[0].upper() # Name of the file
                try: # Extension of the file
                    extension = auxiliar[1].lower()
                except:
                    extension = ''
                if path =='':
                    path = "."
                if extension not  in ['bas', 'b74', 'c74']:
                    tmb.showerror ('Wrong EXTENSION', 'Correct EXTENSIONS: \n bas or b74 for text BASIC CODE.\n c74 for compressed BASIC CODE')
                elif extension == 'bas' or extension == 'b74':
                    Error = 0
                    if self.available_data[BASIC_DATA] == 0:
                        Error = self.Convert_data(BASIC_DATA)
                    if Error ==0:
                        # Update Name, Extension & Path
                        self.Init_data (wave=self.available_data[WAVE_DATA], cassette=self.available_data[CASSETTE_DATA], \
                                        cbasic=self.available_data[CBASIC_DATA], basic=1, \
                                        name=name, extension=extension, path=path)
                        self.wave.set_filename(self.path, self.name)
                        self.basic.set_filename (self.path, self.name, self.extension)
                        self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))
                        self.basic.save_basic()
                    else:
                        tmb.showerror("Conversion ERROR', 'ERROR: {} - {}".format(Error, ERROR_MSG[Error]))  #, "Unable to convert from existing DATA to BASIC")
                elif extension == 'c74':
                    Error = 0 
                    if self.available_data[CBASIC_DATA] == 0:
                        Error = self.Convert_data(CBASIC_DATA)
                    if Error == 0:
                        # Update Name, Extension & Path
                        self.Init_data (wave=self.available_data[WAVE_DATA], cassette=self.available_data[CASSETTE_DATA], \
                                        cbasic=1, basic=self.available_data[BASIC_DATA], \
                                        name=name, extension=extension, path=path)
                        self.wave.set_filename(self.path, self.name)
                        self.basic.set_filename (self.path, self.name, self.extension)
                        self.master.title('{} - {}'.format(self.name, PROGRAM_NAME))
                        self.basic.save_cbasic()
                    else:
                        tmb.showerror("Conversion ERROR', 'ERROR:  {} - {}".format(Error, ERROR_MSG[Error]))  #, "Unable to convert from existing DATA to COMPRESSED BASIC")
        else:
            tmb.showerror ('No DATA', 'LOAD or CREATE a new file first')

    def Play_wave (self):
        if 1 in self.available_data:
            self.ventana = Espere_Window_Obj(titulo='PLAY to TI-74', texto1='Wait until the PLAY process will end', \
                                  texto2='This window will close automatically...', icono='icons/sand-glass-icon-3.gif')

            '''
            self.ventana = tk.Toplevel (self)
            self.ventana.title('PLAY to TI-74')
            self.ventana.geometry('350x160+700+400')
            self.ventana.resizable(False, False)
            self.container = tk.Frame(self.ventana)
            self.container.grid(row=0, column=0)
            self.imagen_WAIT = tk.PhotoImage(file='images/sand-glass-icon-3.gif')
            tk.Label(self.container, text='Wait until the PLAY process will end').pack(padx="10 10", pady="10 5", side=tk.TOP, fill=tk.X)
            tk.Label(self.container, image=self.imagen_WAIT).pack(padx="10 10", pady="10 5", side=tk.TOP, fill=tk.X)
            tk.Label(self.container, text='This window will close automatically...').pack(padx="10 10", pady="10 5", side=tk.TOP, fill=tk.X)
            '''

            # Build and show the window
            self.ventana.overrideredirect(1) # no window decoration
            #self.ventana.transient(self) # dialog window is related to main
            # TODO: Elimniar la accion de botones CERRAR, MINIMIZAR Y MAXIMIZAR o cambiar a lo de OVERRIDEREDIRECT(-1).
            self.ventana.wait_visibility() # can't grab until window appears, so we wait
            self.ventana.grab_set() #The grab_set() method prevents users from interacting with the main window.
            # self.ventana.wait_window() # block until window is destroyed (not necessary now)
            self.ventana.update_idletasks()
            Error = 0 
            if self.arduino_port != None and self.arduino_option.get() == 1:  
                if self.available_data[CASSETTE_DATA] == 0:
                    Error = self.Convert_data(CASSETTE_DATA)
                if Error != 0:
                    tmb.showerror("Conversion ERROR: {} - {}".format(Error, ERROR_MSG[Error]))  #, "Unable to convert from existing DATA to CASSETTE")
                else:
                    self.basic.cassette_section_to_cassette_full()
                    self.arduino.set_data(self.basic.cassette_full)
                    self.arduino.Write_Arduino()
                pass
            else:
                if self.available_data[WAVE_DATA] == 0:
                    Error = self.Convert_data(WAVE_DATA)
                if Error != 0:
                    tmb.showerror("Conversion ERROR: {} - {}".format(Error, ERROR_MSG[Error]))  #, "Unable to convert from existing DATA to WAV")
                else:
                    if self.wave.playable:
                        self.wave.play_data()
            self.ventana.destroy()
        else:
            tmb.showerror("Error", "No DATA data to play")

    def Open_EDIT_Window(self):
        Error = 0
        if 1 not in self.available_data:
            if not(tmb.askyesno('NEW BASIC FILE', 'Do you want to create an empty BASIC TEXT file?')):
                Error = 999
        elif self.available_data[BASIC_DATA] == 0:
            Error = self.Convert_data(BASIC_DATA)
        if Error == 0:
            # Crerate a new Object, it is 'self' to gete the control from this object
            self.Window_02 = EDIT_Window_Obj(name=self.name, basic_text=self.basic.get_basic())
            # To save the new BASIC DATA, we need to control its destroy from this object
            self.Window_02.protocol ("WM_DELETE_WINDOW", lambda: self.Keep_basic_data(True))
            self.Window_02.bind('<Destroy>', self.Keep_basic_data)
            self.Window_02.grab_set() # The grab_set() method prevents users from interacting with the main window.
        elif Error<900:
            tmb.showerror ('Conversion ERROR', ' ERROR: {} - {}'.format(Error, ERROR_MSG[Error]))

    def Keep_basic_data (self, event):
        '''To control the DESTROY of the BASIC TEXT window to be able update the TI-74 BASIC object - TEXT BASIC DATA'''
        # Update the data
        if not(self.Window_02.cancel_edit):
            new_basic = self.Window_02.content_text.get(1.0, 'end').split('\n')
            # Remove the last lines if empty
            while len(new_basic)>0 and len(new_basic[-1]) == 0:
                new_basic.pop()
            self.basic.set_basic(new_basic)
            # The main data is the BASIC TEXT data.
            self.Init_data (basic=1, name=self.name, extension=self.extension, path=self.path)

            # to enable the main window.
        self.Window_02.unbind('<Destroy>')
        self.Window_02.destroy()

    def Open_Settings (self):
        self.Window_03 = Options_Window_Obj(self.wave.input_lista, self.wave.output_lista, self.log_option, self.arduino_option)
        lista = list()
        for i in self.wave.input_lista:
            lista.append(i[1])
        self.Window_03.input_cb['values'] = lista
        self.Window_03.input_cb.current(self.wave.get_input()-self.wave.input_lista[0][0])
        #print ('Input: {}'.format (self.wave.get_input()))
        lista = list()
        for i in self.wave.output_lista:
            lista.append(i[1])
        self.Window_03.output_cb['values'] = lista
        self.Window_03.output_cb.current(self.wave.get_output()-self.wave.output_lista[0][0])
        #print ('Output: {}'.format (self.wave.get_output()))
        # To save the new BASIC DATA, we need to control its destroy from this object
        self.Window_03.protocol ("WM_DELETE_WINDOW", lambda: self.Close_Settings(True))
        # self.Window_03.bind('<Destroy>', self.Keep_basic_data)
        self.Window_03.grab_set() # The grab_set() method prevents users from interacting with the main window.
        self.Window_03.bind('<<CloseSettings>>', self.Close_Settings)

    def Close_Settings(self, event):
        if not(self.Window_03.cancel_options):
            # Update the selected settings
            self.wave.set_input(self.Window_03.input_cb.current()+self.wave.input_lista[0][0])
            self.wave.set_output(self.Window_03.output_cb.current()+self.wave.output_lista[0][0])
            self.log_option.set(self.Window_03.log_file.get())            
            # checking Arduino option and log the updated option if necessary
            if self.arduino_port != None:
                if self.Window_03.arduino_opt.get() != self.arduino_option.get():
                    if self.Window_03.arduino_opt.get() == 0:
                        self.arduino_label.configure(image=self.arduino_off)
                    else:
                        self.arduino_label.configure(image=self.arduino_on)
                if self.Window_03.arduino_opt.get() == 1 and self.arduino_option.get() == 0 and self.log_option.get() == 1:
                    self.log_file.write ('\nUsing arduino LEONARDO  to REC/PLAY: {:s}\n\n'.format('YES' if self.Window_03.arduino_opt.get()==1 else 'NO'))
                self.arduino_option.set(self.Window_03.arduino_opt.get())
            # Logging the INITIAL options
            if self.log_option.get() == 1:
                if not(self.save_log):
                    self.save_log=True
                    self.log_file = open ('cnv_log.txt', 'w')
                    self.log_file.write('CONVERSION LOG FILE.\n')
                    self.log_file.write('====================\n\n')
                    self.log_file.write ("Date and time: %s\n\n" % datetime.datetime.now())
                    if self.arduino_port != None:
                        self.log_file.write ('Arduino LEONARDO found in port: {:s}\n'.format(self.arduino_port))
                        self.log_file.write ('Using arduino LEONARDO to REC/PLAY: {:s}\n\n'.format('YES' if self.arduino_option.get()==1 else 'NO'))
                    else:
                        self.log_file.write ('Arduino LEONARDO NOT found.\n\n')
        self.Window_03.unbind('<<CloseSettings>>')
        self.Window_03.destroy()       

    def Close_app (self):
        if self.save_log:
            # Close the log file
            self.log_file.close()
        self.wave.terminate()
        self.master.destroy()




if __name__ == "__main__":
    if tk.TkVersion < 8.6:
        print("tkinter.TkVersion is {tk.TkVersion}. Version 8.6 or higher is required.")
        exit(1)

    root = tk.Tk()
    #root.wm_title(PROGRAM_NAME) # Esta es una manera de poner el título
    app = Principal (master=root)
    root.mainloop()

