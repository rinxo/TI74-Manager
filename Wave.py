#import wave
#import numpy as np
import matplotlib.pyplot as plt
from Grabar_Audio import AudioFile, FORMAT, CHANNELS, RATE, CHUNK_SIZE
from array import array
from cas2b74 import TI75_Basic, SYNCRO_BLOCK_NUM_ZEROS, SYNCRO_BLOCK, BLOCK_END_ID
#import time

UMBRAL_RATE = 0.80
CASSETTE_FREQUENCIA = 1400
CERO = 1
UNO = 0.5
RATE_CERO = 125
RATE_UNO = 115
CERO_AMP = int(CERO * RATE_CERO)
UNO_AMP = int(UNO * RATE_UNO)
SALTO_AMP = 2
WAVE_FREQ = 44100 # Wav sample frequency
WAVE_ONE = [[0, 14, 0, -15], [0, 15, 0, -15]] # ONE wave samples
WAVE_ZERO = [[0, 30], [0, 31]] # ZERO wave samples
WAVE_WIDTH = 32000
INITIAL_TIME = 0.2 #Initial time in seconds before starting the data
INTERMEDIATE_TIME = 0.1 # Time time between two sections 
N_DATA_WAVE_EVEN = 31 # Number fo data to conform an even wave (par)
N_DATA_WAVE_ODD = 32 # Number fo data to conform an odd wave (impar)
WAVE_AMP = 32000 # Wave depth (amplitud).


'''
NOTE: Wave file sample is 44100 (number of data per second) and the cassette 
frequency is 1400 bits per second, that means 44100/1400 = 31.5 data per bit
or 63 data for each two bits, therefore the first bit (even) will have 31 
datas and the second one (odd) 32 datas.

The ZERO bit is a wave with a wave lenght of 1/700 seconds and the ONE wave
has a wave length of 1/1400 seconds. To get bit rate of 1400 means the half 
of ZERO wave will provide a bit and the complete ONE wave will provide a bit 

The wave is represented as a list, where the values are:
    0: data sample is ZERO, in the X axes.
    x: Number of data sample above (positive) or below (negative) of X axes.
    BIT Sample type:    ONE:                       ZERO:
                       /-x-\                       /-x-
        X axes--->   -/     \_      X axes--->   -/
                              \     
                               -x-               
    Those samples are for 1400 bits per second and the ZERO is just the half,
    therefore, the wave is represented starting as positive, in case the 
    starting is negative then multiply the wave sample by -1.
    '''

def Pendiente (x1, x2, dist):
    return (float(x2)-float(x1))/float(dist)

def sign(a):
    a=float(a)
    return (a > 0) - (a < 0)

def Interseccion (x1, y1, x2, y2):
    # Intersección en el eje X
    try:
        x = y1*(x1-x2)/(y2-y1)+x1
        return x
    except:
        return None

class TI75_AudioFile (AudioFile):
    def __init__(self, file_name, formato=FORMAT, channels=CHANNELS, rate=RATE, chunk=CHUNK_SIZE, input_device=None, output_device=None):
        super().__init__(file_name, formato, channels, rate, chunk, input_device, output_device)
        self.cassette_section=list()

    def wav_to_cassette_section (self, log_file=False, file=None):
        '''
        ----  CONVERT WAVE DATA TO RAW (bytes) ----
        
        It is computed the distance between two consecutive intersections in the X-axis, only when the UMBRAL_RATE times WAVE AMPLITUD 
        is reached, otherwise the intersection is rejected.

        Creates a list with the different sections of the wave data. Each section of the wave is a byte string ending with
        the character 0xff
        '''
        umbral_mas = max(self.data_all)*UMBRAL_RATE
        umbral_menos = min(self.data_all)*UMBRAL_RATE
        if log_file:
            file.write ('CONVERSION FROM WAV FILE TO RAW CASSETTE SECTION\n\n')
            file.write ('File: {:s}\n'.format(self.file))
            file.write ('  - Data format: {:d}\n'.format(self.format))
            file.write ('  - Number of channels: {:d}\n'.format(self.nchannels))
            file.write ('  - Sample rate: {:d}\n'.format(self.rate))
            file.write ('  - Chunk data: {:d}\n'.format(self.chunk))
            file.write ('MAXIMUM DATA VALUE : {:7d}\n'.format(max(self.data_all)))
            file.write ('MINIMUMN DATA VALUE: {:7d}\n'.format(min(self.data_all)))

        # Analizamos cuando pasa de positivo a negativo
        # INICIALIZAMOS: 
        #   - Lado en el que nos encontramos
        #   - Máximo, mínimo y tiempo inicial
        lado1 = sign(self.data_all[0])
        minimo=self.data_all[0]
        maximo=self.data_all[0]
        i1=0
        tiempo1 = 0
        datos= list()
        num_bytes = list()
        datos.append(array('B'))
        seccion=0
        bits=0.0
        for i in range(1, len(self.data_all)):
            if self.data_all[i]>maximo:
                maximo=self.data_all[i]
            elif self.data_all[i]<minimo:
                minimo=self.data_all[i]
            lado2 = sign (self.data_all[i])
            if lado2 !=0:
                if lado1 != lado2:
                    # Cambio de POSITIVO a NEGATIVO, calculamos el tiempo en el cruce del eje X.
                    tiempo2 = Interseccion(float(i1)/self.rate, float(self.data_all[i1]), float(i)/self.rate, float(self.data_all[i]))
                    if tiempo2 != None:
                        # Verificamos si se ha alcanzado el umbral
                        if (lado1 == 1 and maximo > umbral_mas) or (lado1==-1 and minimo<umbral_menos):
                            if tiempo1 != 0:
                                tiempo = (tiempo2-tiempo1)*CASSETTE_FREQUENCIA
                                if tiempo>SALTO_AMP:
                                    # Cambio de sección
                                    if len(datos[seccion])>0:
                                        # Añadimos el último 0.5
                                        datos[seccion].append(int(UNO*100))
                                        bits += 0.5
                                        # Último dato de la sección es el número de bits
                                        num_bytes.append(bits)
                                        bits=0
                                        seccion +=1
                                        datos.append(array('B'))
                                elif tiempo > UNO_AMP:
                                    bits += 1
                                    datos[seccion].append (int(tiempo*100))
                                else:
                                    bits += 0.5
                                    datos[seccion].append (int(tiempo*100))
                        # en cualquier caso avanzamos el tiempo y actualizamos los máximos y mínimos
                        tiempo1 = tiempo2
                        maximo=0
                        minimo=0
                # Tiempo del último cambio de POSITIVO a NEGATIVO
                i1=i
                lado1=lado2
        # Imprimimos los cambios
        # Si el último elemento de la sección NO está vacio, se incrementa el número de SECCIONES
        # y se cierra el último 0xFF
        if len (datos[seccion]) != 0:
            datos[seccion].append(int(UNO*100))
            bits += 0.5
            # Añadimos el número de bits
            num_bytes.append(bits)
        # Eliminamos las secciones vacias
        while len(datos[len(datos)-1]) == 0:
            datos.pop()
        seccion =len(datos)

        if log_file:
            file.write ('Number of sections    : {:#x}\n'.format(seccion))
            file.write ('Number of bits        :')
            for i in range(seccion):
                file.write ('{:10d}'.format(int(num_bytes[i])))
            file.write ("\n")
            file.write ('Number of bytes as INT:')
            for i in range(seccion):
                file.write ('{:10d}'.format(int(num_bytes[i])//8))
            file.write ("\n")
            file.write ('Number of bytes as HEX:')
            for i in range(seccion):
                file.write ('{:#10x}'.format(int(num_bytes[i]//8)))
            file.write ("\n")
            file.write ('Remainig bytes as DEC :')
            for i in range(seccion): 
                file.write ('{:10d}'.format(int(num_bytes[i] % 8)))
            file.write ("\n")

            file.write ("\n")
            file.write ('===============================================================\n')
            file.write ("\n")

            for i in range(seccion):
                if len(datos[i]) > 20:
                    file.write ('START of Section: {:3d}:'.format(i+1))
                    for j in range(0,20):
                        file.write ('{:5d}'.format(datos[i][j]))
                    file.write ('\n')
                    file.write ('END of Section  : {:3d}:'.format(i+1))
                    for j in range(len(datos[i])-20,len(datos[i])):
                        file.write ('{:5d}'.format(datos[i][j]))
                    file.write ('\n')
                    file.write ('\n')

        # Ahora iremos sección por sección a interpretar los bits y convertirlos a bytes
        # Lets do a small checking
        if seccion == 4:
            self.cassette_section=list()
            for i in range(seccion):
                bits=0
                empezar=False
                self.cassette_section.append(b'')
                valor=0b00
                j=0
                primerdato = True
                while j<len(datos[i]):
                    if not(empezar) and j<(len(datos[i])-1):
                        # If next data is different to ZERO, then will start from next data.
                        if datos[i][j+1]<UNO_AMP:
                            empezar=True
                    else:
                        #desplazamos un bit hacia la izquierda
                        valor=valor<<1
                        # si es uno añadimos la unidad
                        if datos[i][j]<UNO_AMP:
                            valor +=0b01
                            # Saltamos uno
                            j += 1
                        bits +=1
                        # If the byte is complete, then upload
                        if bits==8:
                            if primerdato:
                                primerdato=False
                                if valor != BLOCK_END_ID:
                                    # Error: Unexpected symbol at the end of syncro block
                                    return 1
                            else:
                                self.cassette_section[i] += valor.to_bytes(1,'little')
                            # Comenzamos un nuevo
                            valor=0b00
                            bits=0
                    j+=1
                if log_file:
                    file.write ('SECTION {:d}:\n'.format(i))
                    file.write ('Data type: {:s} ----> {} ---ES---> {:#x}\n'.format(str(type(self.cassette_section[i])), self.cassette_section[i], self.cassette_section[i][-1]))
                if self.cassette_section[i][-1] != BLOCK_END_ID:
                    # Error: Unexpected symbol at the end of current block
                    if log_file:
                        file.write ('ERROR: {:d}: Unexpected symbol at the end of current block'.format((i+1)*10+1))
                    return (i+1)*10+1
                if log_file:
                    file.write ("\n")
            # TODO: Check the integrity of the data...            
            return 0
        else:
            return 90 # Insufficient number of SECTIONS.
    
    def cassette_section_to_wave (self, log_file=False, file=None):
        """
        Convert the COMPLETE RAW (includes the syncro section) data to a WAVE format.
        """

        # Calculate the total number of data
        num_datos = 0
        secciones = len(self.cassette_section)
        for i in range(secciones):
            num_datos += len(self.cassette_section[i])
        num_datos += int(secciones*(len(SYNCRO_BLOCK)))
        total_datos = int(int(num_datos*4) * (N_DATA_WAVE_EVEN+N_DATA_WAVE_ODD) + \
            (int(num_datos*8)%2) * N_DATA_WAVE_ODD + int((INITIAL_TIME+INTERMEDIATE_TIME*secciones)*WAVE_FREQ))
        # Basic data to the log file
        if log_file:
            file.write ('CONVERSION FROM RAW CASSETTE SECTION TO WAVE\n')
            file.write ('  - Data format: {:d}\n'.format(self.format))
            file.write ('  - Number of channels: {:d}\n'.format(self.nchannels))
            file.write ('  - Sample rate: {:d}\n'.format(self.rate))
            file.write ('  - Chunk data: {:d}\n'.format(self.chunk))
            file.write ('  - Total number of data to write: {:d}\n'.format(total_datos))
        # Create an ARRAY wiht zeros and size the total_datos.
        self.data_all=array('h',[0]*total_datos)
        # Forward the INITIAL_TIME.
        i = int(INITIAL_TIME * RATE)
        sentido = 0b00   # An aux variable to know if the wave starts as positive or negative, the direction.
        par_impar = 0b01 # An aux variable to know if the data is odd or even (number of data).
        for n in range (secciones):
            # Only ONE variable with the syncro block and the consecutive data... 
            data_block = SYNCRO_BLOCK + self.cassette_section[n]
            for j in range (len(data_block)):
                byte_data=data_block[j]
                for k in range(7, -1, -1):
                    # We check bit by bit to upolioad each wave data
                    mascara = 0b00000001 << k
                    # change from odd to even or viceversa.
                    par_impar = par_impar ^ 0b01
                    if byte_data & mascara == mascara:
                        # This is ONE (UNO), it uses the complete vawe.
                        for onda in WAVE_ONE[par_impar]:
                            if onda != 0:
                                if sentido == 0:
                                    valor = int(sign(onda) * WAVE_AMP)
                                else:
                                    valor = -int(sign(onda) * WAVE_AMP)
                                for l in range(abs(onda)):
                                    self.data_all[i]= valor
                                    i += 1
                            else:
                                i += 1 
                    else: 
                        # This is ZERO (CERO), it uses the half of the complete wave only.
                        for onda in WAVE_ZERO[par_impar]:
                            if onda != 0:
                                if sentido == 0:
                                    valor = int(sign(onda) * WAVE_AMP)
                                else:
                                    valor = -int(sign(onda) * WAVE_AMP)
                                for l in range(abs(onda)):
                                    self.data_all[i]= valor
                                    i += 1
                            else: 
                                i += 1 
                        # Due to the use of the half of the wave, to change the direction (sentido).
                        sentido = sentido ^ 0b01
            i += int(WAVE_FREQ * INTERMEDIATE_TIME)
        self.playable=True
        if log_file:
            file.write ('Process ends.\n\n')

    def set_cassette_section (self, raw_section):
        '''Returns  list with four sections of the CASSETTE file as binary objects'''
        self.cassette_section = raw_section
        return

    def get_cassette_section (self):
        '''Returns  list with four sections of the CASSETTE file as binary objects'''
        return self.cassette_section



def main():

    # Open the WAV file example
    a = TI75_AudioFile('./Examples/Largo16-bit.wav')
    # Read a WAVE file.
    a.read_file()

    # Convert WAVE file to a list of binary cassette per sections.
    Error= a.wav_to_cassette_section (False)

    # Convert the binary cassette per sections to WAVE
    #a.cassette_section_to_wave()

    # Play the WAVE in memory.
    #a.play_data()

    # Create a TI-74 code basic object with a list of binary cassette per sections from above.
    b = TI75_Basic ('pepe', raw_cassette=a.get_cassette_section())

    # Convert the list of binary cassette to compressed basic.
    b.cassette_section_to_cbasic()

    # Convert the list of binary cassette to complete binary cassette.
    b.cassette_section_to_cassette_full()

    # Convert the compressed basic to a text basic code. 
    b.cbasic_to_basic()

    # Convert the complete binary cassette to list of binary cassette.
    b.cassette_full_to_cassette_section()

    # Convert the list of binary cassette to compressed basic.
    b.cassette_section_to_cbasic()

    # Convert the compressed basic to a text basic code.
    b.cbasic_to_basic()

    # Convert the text basic code to compressed basic.
    b.basic_to_cbasic()
   
    # Convert the compressed to list of binary cassette.
    b.cbasic_to_cassette_section()
 
    a.terminate()

    

if __name__ == "__main__":
    main()    