# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 19:00:38 2022

@author: rinxo
"""

''' ERRORS:
  -  1: Unexpected symbol at the end of syncro block.
  -  2: Syncro Block has not end.
  -  3: Syncro block shorter then exepected.
  - 10: CheckSum Error: SECTION 1, FIRST BLOCK.
  - 11: Unexpected symbol at the end of the block: SECTION 1, FIRST BLOCK.
  - 12: Name len higher than maximun: SECTION 1, FIRST BLOCK
  - 13: Number of insufficient data:  SECTION 1, FIRST BLOCK.
  - 20: CheckSum Error: SECTION 1, SECOND BLOCK.
  - 21: Unexpected symbol at the end of the block: SECTION 1, SECOND BLOCK.
  - 23: Number of insufficient data:  SECTION 1, SECOND BLOCK.
  - 30: CheckSum Error: SECTION 3, PROGRAM CODE ID BLOCK.
  - 31: Unexpected symbol at the end of the block: PROGRAM CODE ID BLOCK.
  - 33: Number of insufficient data:  SECTION 3, ID BLOCK.
  - 40: CheckSum Error: SECTION 3, PROGRAM CODE BLOCK.
  - 41: Unexpected symbol at the end of the block: FOURTH BLOCK.
  - 43: Number of insufficient data:  SECTION 3, CODE BLOCK.
  - 90: Insufficient number of SECTIONS.
  -100: No DATA: LOAD or CREATE a new data file first.
  -999: Any other else. Example do not continue the execution.

'''

from array import array
from struct import pack, unpack
from sys import byteorder
import copy
import pyaudio
import wave

THRESHOLD = 500  # audio levels not normalised.
CHUNK_SIZE = 1024
RATE = 44100
SILENT_CHUNKS = 5 * RATE / CHUNK_SIZE  # about 3sec
FORMAT = pyaudio.paInt16 # signed 16-bit binary string. 15 bits for the number, and one for the sign.
FRAME_MAX_VALUE = 2 ** 15 - 1
NORMALIZE_MINUS_ONE_dB = 10 ** (-1.0 / 20)
CHANNELS = 1
TRIM_APPEND = RATE / 4

# NB: FORMAT is not equivalente to SAMPLE WIDTH, but thre is a specific function to convert one to the other and viceversa. 

class AudioFile:
    default_channel = 0

    def __init__(self, file_name, formato=FORMAT, channels=CHANNELS, rate=RATE, chunk=CHUNK_SIZE, input_device=None, output_device=None):
        """ Init audio stream """
        # opne the Audio channel, and initial bonding of the variables
        self.p = pyaudio.PyAudio()
        self.file=file_name + '.wav'
        self.format = int(formato)
        self.nchannels = int(channels)
        self.rate = int(rate)
        self.chunk = int(chunk)
        try:
            self.input_device_index = int(input_device)
        except:
            self.input_device_index = input_device
        try:
            self.output_device_index = int(output_device)
        except:
            self.output_device_index = output_device
        self.data_all = array('h') # Array with the Audio data
        self.playable = False
        self.input_lista = self.list_devices('maxInputChannels')
        self.set_input(self.input_lista[0][0])
        self.output_lista = self.list_devices('maxOutputChannels')
        self.set_output(self.output_lista[0][0])
        self.cotinue_REC = True
        self.recording = False

    def set_default (self):
        self.format = FORMAT
        self.nchannels = CHANNELS
        self.rate = RATE
        self.chunk = CHUNK_SIZE        

    def set_input (self, value=None):
        self.input_device_index = int(value)

    def get_input (self):
        return self.input_device_index

    def set_output (self, value=None):
        self.output_device_index = int(value)

    def get_output (self):
        return self.output_device_index

    def list_devices (self, token='maxInputChannels'):
        """ Devuelve una lista con los dipositivos de AUDIO. Los tokes disponibles son:
            - maxInputChannels:  Para obtener los dispositivos de entrada de audio, y
            - maxOutputChannels: Para obtener los dispositivos de salida  de audio

            La lista se cmpone de pares de datos, cada par contiene como primer índice 
            el ID del dispositivo y el segundo es su nombre.
        """
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        device_lista = list()
        for i in range(0, numdevices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get(token)) > 0:
                # print ("Input Device id ", i, " - ", self.p.get_device_info_by_host_api_device_index(0, i).get('name'))
                device_lista.append((i,self.p.get_device_info_by_host_api_device_index(0, i).get('name')))
        return device_lista

    def read_file (self):
        #Open a file
        wave_file = wave.open(self.file, 'rb')
        # Read the file specs: format, channels and rate
        self.format = self.p.get_format_from_width(wave_file.getsampwidth()) # Convert the SAMPLE_WIDTH wave to FORMAT pyAudio style
        self.nchannels = wave_file.getnchannels()
        self.rate = wave_file.getframerate()
        # Read the complete file
        data = wave_file.readframes(-1)
        self.data_all = array('h')
        data=list(unpack('h' * int(len(data)/2), data))
        # Keep the default channel: 0
        self.data_all.fromlist(data[AudioFile.default_channel:len(data):self.nchannels])
        # Fix channels to ONE channel only.
        self.nchannels = CHANNELS
        #Close the file
        wave_file.close()
        # It would be possible to play the data
        self.playable = True

    def record_to_file(self):
        # Records from the selected source to an Array
        self.record_data()
        # save to a file...
        if self.playable: # Save to a file if ther is correct data.
            self.save_data_to_file()

    def save_data_to_file (self):
        # Save the recorded data to a file.

        # Convert to binary String, keeping the original data...
        data = pack('<' + ('h' * len(self.data_all)), *self.data_all)
        '''la linea de ariba es lo mismo que
        for i in range(len(self.data_all)):
            self.data_all[i] = pack ('<h', self.data_all[i])'''

        # Save the Wav file
        wave_file = wave.open(self.file, 'wb')
        wave_file.setnchannels(self.nchannels)
        wave_file.setsampwidth(self.p.get_sample_size(self.format)) #Convert the FORMAT pyAudio to SAMPLE_WIDTH  wave style.
        wave_file.setframerate(self.rate)
        wave_file.writeframes(data)
        wave_file.close()

    def stop_REC (self):
        self.cotinue_REC = False

    def get_recording (self):
        return self.recording

    def set_recording(self, valor=False):
        self.recording=valor

    def set_playable (self, valor=False):
        self.playable = valor

    def set_filename (self, path, name):
        self.file = path + '/' + name + '.wav' 

    def record_data(self):
        """Record a word or words from the microphone and 
        return the data as an array of signed shorts."""

        self.recording = True
        # Open the Stream for recording...
        stream = self.p.open(format=self.format, channels=self.nchannels, rate=self.rate,
            input=True, output=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk)


        silent_chunks = 0
        audio_started = False
        # Initialize the array and data
        self.data_all = array('h')
        self.continue_REC = True
        self.playable = False

        while self.continue_REC:
            # little endian, signed short
            data_chunk = array('h', stream.read(CHUNK_SIZE))
            if byteorder == 'big':
                data_chunk.byteswap()
            self.data_all.extend(data_chunk)

            silent = is_silent(data_chunk)

            if audio_started:
                if silent:
                    silent_chunks += 1
                    if silent_chunks > SILENT_CHUNKS:
                        self.playable = True
                        break
                else: 
                    silent_chunks = 0
            elif not silent:
                silent_chunks = 0
                audio_started = True
            else:
                silent_chunks += 1
                if silent_chunks > SILENT_CHUNKS:
                    break
        if self.continue_REC and self.playable:
            stream.stop_stream()
            stream.close()

            self.data_all = trim(self.data_all)  # we trim before normalize as threshhold applies to un-normalized wave (as well as is_silent() function)
            self.data_all = normalize(self.data_all)
            self.playable = True
        else:
            self.playable = False

        self.recording=False

    def play_file(self):
        # Open the file to play
        wave_file = wave.open(self.file, 'rb')
        # Read the file specs: format, channels and rate
        self.format = self.p.get_format_from_width(wave_file.getsampwidth()) # Convert the SAMPLE_WIDTH wave to FORMAT pyAudio style
        self.nchannels = wave_file.getnchannels()
        self.rate = wave_file.getframerate()
        # Open the Stream for reading.
        stream = self.p.open(
            format = self.format,
            channels = self.nchannels,
            output_device_index=self.output_device_index,
            rate = self.rate,
            output = True
        )
        # Play entire file.
        data = wave_file.readframes(self.chunk)
        while len(data) != 0:
            stream.write(data)
            data = wave_file.readframes(self.chunk)
        # Close the file
        wave_file.close()
        # Close the stream.
        stream.close()

    def play_data(self):

        if self.playable:
            # Open the Stream for reading.
            stream = self.p.open(
                format = self.format,
                channels = self.nchannels,
                output_device_index=self.output_device_index,
                rate = self.rate,
                output = True
            )
            # Play the data...
            blocks=int(len(self.data_all)/self.chunk)
            for i in range(blocks):
                startindex=i*self.chunk
                data = self.data_all[startindex:startindex+self.chunk]
                # Convert to binary String
                data = pack('<' + ('h' * len(data)), *data)
                stream.write(data)
            # The remain block...
            remain_block= len(self.data_all)%self.chunk
            if remain_block !=0:
                data = self.data_all[-remain_block:]
                # Convert to binaru String.
                data = pack('<' + ('h' * len(data)), *data)
                stream.write(data)
            
            # Close the stream.
            stream.close() 
        else:
            #print ('No data recorded to play.....')
            pass

    def terminate(self):
        """ Graceful shutdown """ 
        self.p.terminate()


""" GENERAL SUBRUTINES
    ================== """
def is_silent(data_chunk):
    """Returns 'True' if below the 'silent' threshold"""
    return max(data_chunk) < THRESHOLD

def normalize(data_all):
    """Amplify the volume out to max -1dB"""
    # MAXIMUM = 16384
    normalize_factor = (float(NORMALIZE_MINUS_ONE_dB * FRAME_MAX_VALUE)
                        / max(abs(i) for i in data_all))

    r = array('h')
    for i in data_all:
        r.append(int(i * normalize_factor))
    return r

def trim(data_all):
    _from = 0
    _to = len(data_all) - 1
    for i, b in enumerate(data_all):
        if abs(b) > THRESHOLD:
            _from = int(max(0, i - TRIM_APPEND))
            break

    for i, b in enumerate(reversed(data_all)):
        if abs(b) > THRESHOLD:
            _to = int(min(len(data_all) - 1, len(data_all) - 1 - i + TRIM_APPEND))
            break

    return copy.deepcopy(data_all[_from:(_to + 1)])



if __name__ == '__main__':

    a = AudioFile("./Examples/pepe.wav")


    # a = TI75_AudioFile("1.wav")
    # Seleccionamos dispositivo de entrada:
    print("Seleccione el dispositivo de entrada....")
    for i in range(len(a.input_lista)):
        print (i, ' ---> (',a.input_lista[i][0],')' ,a.input_lista[i][1])
    Entrada = -5
    while Entrada not in range(len(a.input_lista)):
        try:
            Entrada = int(input ('Select input: (0=Default): '))
        except:
            pass
    a.set_input(Entrada+a.input_lista[0][0])
    print ("\n=================================\n")
    # Seleccionamos dispositivo de salida:
    print("Seleccione el dispositivo de salida....")
    for i in range(len(a.output_lista)):
        print (i, ' ---> (',a.output_lista[i][0],')',a.output_lista[i][1])
    Entrada = -5
    while Entrada not in range(len(a.output_lista)):
        try:
            Entrada = int(input ('Select input: (0=Default): '))
        except:
            pass
    a.set_output(Entrada+a.output_lista[0][0])
    print("Write SAVE \"1.file_name\" and  ENTER two times in the TI-75 to start recording.....\nThe recording will end automatically")

    a.read_file()
    #a.record_to_file()
    #a.record()
    print("done - result written to demo.wav\n\n\n")
    print ("Write VERIFY \"1.file_name\" and  ENTER two times in the TI-75 to verify the recording.")
    print ("Press ENTER key to when ready.")
    input()
    # a.play_file()
    a.play_data()
    print ('End of all processes....')
    a.terminate()
