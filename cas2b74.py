# PROGRAMA PARA CONVERTIR LOS ARCHIVOS DE CASSETTE DE LA TI-74 A BASIC
# Los archivos han subi al pc en formato binario por medio de la ARDUINO
# 
# REFERENCES:
#   http://www.mvcsys.de/  Marcus von Cube and the CASUTIL.ZIP 
#   https://github.com/molleraj/ti95interface    Abraham Moller, 2022

# Formato de los archivos binarios:
# 
# Los primeros 1208 bytes con "0x00" + 0xFF --> Se usan para sincronizar.
# 
# SECCION IDENTIFICADOR NOMBRE:
#    - Bloque ID
#      0x00 0xZZ 0x00 0x00 0xZZ 0x84 0xSU --> ZZ numero de datos del bloque sección nombre (no incluye el CheckSum).
#                                             SU CheckSum del bloque de datos.
#      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
#      Repetición bloque e indicación de fin de bloque.
#    - Bloque nombre
#      0xHH 0xGG 0x80 0xII ... 0xYY 0xSU  --> GGHH (Word) Número total de datos (bloque programa+bloque variables). Orden inverso LB+HB.
#                                             II ... YY Caracteres ASCII del Nombre de archivo.
#                                             SU CheckSum del bloque.
#      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
#      Repetición bloque, NO se repite la indicación de fin de bloque.
#      0xFF
#
# 1208 "0x00" +0xFF --> Se usan para sincronizar.
#
# SECCION DESCONOCIDA, en todos los programas es igual.
#      0x00 0x00 0x00 0x00 0x00 0xC2 0xSU  -> SU CheckSum del bloque.
#      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
#      Repetición bloque, NO se repite la indicación de fin de bloque.
#      0xFF
#
# 1208 "0x00" +0xFF --> Se usan para sincronizar.
#
# SECCIÓN PROGRAMA.
#    - Bloque identificador.
#      0xGG 0xHH 0xII 0xJJ 0xKK 0x82 0xSU --> GGHH (Word) Número total de datos (bloque programa+bloque variables). 
#                                             Contando a apartir de "a".
#                                             IIJJ (Word) Número de bloques de 64 bytes de datos.
#                                             KK Número de bytes del último bloque. 
#                                             IIJJ x 40 + KK = GGHH         
#      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
#      Repetición bloque e indicación de fin de bloque.
#    - (a) Bloque programa.
#      0x80 0x03 0xLL 0xMM                --> MMLL Número total datos del Bloque programa. Orden inverso LB+HB. 
#                                             Contando a partir de "b". 
#      (b) Vienen las líneas de programa como:
#      0xNN 0xPP 0xRR datos 0x00          --> PPNN Línea del programa, orden inverso LB+HB.
#                                             RR número de datos en la línea, incluye RR+datos+00.
#      La última línea del programa siempre es:
#      0xFF 0x 7F 0x03 0x86 0x00
#    - Bloque Variables (están en orden inverso a como se crearon).
#      0xSS                               --> Primera variable libre de la TI-74 (no usada).
#      Viene el listado de variables, por cada una:
#              0xTT datos                 --> TT Número de caracteres de la variable
#                                         --> Caracters ASCII de la variable, al último carácter hay que 
#                                             poner a CERO su primer bit (and 0x7F). 
#              0x00                       --> Terminación del bloque.
#      En la sección de programa+variables, cada vez que se escriben 0x40 bytes (o menos), se añade:
#             Checksum (del sub-bloque) + 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF
#      Se vuelve a escribir el bloque
#      Si no se ha terminado, se añade  
#             Checksum (del sub-bloque) + 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF
#      Se prosigue con el siguiente sub-bloque de 0x40 (o menos)
#      
#      Cuando se termine con la segunda copia del último sub-bloque:
#      0xSU                               --> CheckSum del último sub-bloque programa y variables
#      0xFF
#

# 1208 "0x00" +0xFF --> Se usan para sincronizar.
#
# SECCION DESCONOCIDA, en todos los progrmas es igual.
#      0x00 0x00 0x00 0x00 0x00 0xC1 0xSU  -> SU CheckSum del bloque.
#      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
#      Repetición bloque, NO se repite la indicación de fin de bloque.
#
#
# REPRESENTACIÓN DE UN NÚMERO
# Los números van precedidos de uno de los siguientes códigos: 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, donde el   
# dígito numérico representa en numero de bytes que componen el número, se hace 0xCX and 0x7F para quedarnos con 
# el número de caracteres. El primer carácter representa el exponente sobre 10, se obtiene como 2 x 0xEXP - 0x7F,
# ya lleva su signo correspondiente. El resto de caracteres es la representación simbólica del numero como
# LM NO PQ RS TU VW XY, según el número que tenga de caracteres y su representación es: L,MNOPQRSTUVWXY E Expo
# donde e represente 10 elevado a Expo

import sys

'''CONSTANT DEFINITION'''
OFFSET_NAME = 3 # Número de bytes antes del nombre de archivo. 
CS = 1 # Número de bytes que definen el CheckSum.
ES = 1 # Número de bytes que definen el fin de sección.
BU = 8 # Numero de bytes que separan los datos entre backups o sub-secciones. 
SEPARADOR = [':',' ','"',",",";",")","=",">","<","&","+","-","*","/","^","(","#",'!']
CARACTER_NUMERICOS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '-', '.', 'E']
MAX_SYNCRO_DATA = 1400 # Maximum number of ZEROS in the syncro block.
SYNCRO_BYTE = 0x00 # The typical syncro data.
BLOCK_END_ID = 0xff # The byte that indicates the end of a block.
SYNCRO_BLOCK_NUM_ZEROS = 1208 # Numbers of Zeros to syncro. 
SYNCRO_BLOCK =  (bytes(SYNCRO_BLOCK_NUM_ZEROS)) + 0xff.to_bytes(1,'little')
MIN_SYNCRO_ZERO = 10
MAX_LEN_FILE_NAME = 18
SECTION_2 =  (bytes(5)) + 0xc2.to_bytes(1,'little') + 0xc2.to_bytes(1,'little') + (bytes(8)) + 0xff.to_bytes(1,'little') +\
           (bytes(5)) + 0xc2.to_bytes(1,'little') + 0xc2.to_bytes(1,'little') + 0xff.to_bytes(1,'little')
SECTION_4 =  (bytes(5)) + 0xc1.to_bytes(1,'little') + 0xc1.to_bytes(1,'little') + (bytes(8)) + 0xff.to_bytes(1,'little') +\
           (bytes(5)) + 0xc1.to_bytes(1,'little') + 0xc1.to_bytes(1,'little') + 0xff.to_bytes(1,'little')
SECTION1_BLOCK1_NUM_DATA = 6 + CS + BU + ES
SECTION1_BLOCK2_NUM_DATA = OFFSET_NAME + CS + ES
SECTION3_ID_NUM_DATA = 6 + CS + BU + ES
CODE_CS_ERROR = 40 # Error code for CheckSum error.

"""============================================================================================
 TOKEN DEFINITION
============================================================================================"""
# Tokens start by hex 0x81 and goes till to 0xFF (127 tokens) and they are consecutive. To get 
# the correct token the byte value must be deducted by 0x81
# Exceptions:
#    "\\C2",      /* BCD number (2 Byte) 1-2 digits */
#    "\\C3",      /* BCD number (3 Byte) 3-4 digits */
#    "\\C4",      /* BCD number (4 Byte) 5-6 digits */
#    "\\C5",      /* BCD number (5 Byte) 7-8 digits */
#    "\\C6",      /* BCD number (6 Byte) 9-10 digits */
#    "\\C7",      /* BCD number (7 Byte) 11-12 digits */
#    "\\C8",      /* BCD number (8 Byte) 13-14 digits */
# The number o digts is ID-0xc1, without the exponential part
#    "\\C9",      /* "Quoted String" */
#    "\\CA",      /* String without quotes */
#    "\\CB",      /* binary value */
TOKENS = ['DISPLAY', 'REM', 'DIM', 'IMAGE', 'STOP', 'END', 'LET', 'INPUT', 'LINPUT', 
          'PRINT', 'PAUSE', 'OPEN', 'CLOSE', 'RESTORE', chr(0x8f), 'RANDOMIZE', 'ON',
          'GOTO', 'GOSUB', 'RETURN', 'CALL', chr(0x96), chr(0x97), 'SUB', 'SUBEXIT',
          'SUBEND', 'FOR', 'NEXT', 'IF', 'ELSE', chr(0x9f), '!', 'READ', 'DATA', 
          'ACCEPT', chr(0xa4), chr(0xa5), chr(0xa6), chr(0xa7), chr(0xa8), chr(0xa9),
          'THEN', 'TO', 'STEP', ',', ';', ')', 'OR', 'AND', 'XOR', '<>', '<=', '>=',
          '=', '<', '>', '&', '+', '-', '*', '/', '^', chr(0xbf), '(', 'NOT', 
          chr(0xc2), chr(0xc3), chr(0xc4), chr(0xc5), chr(0xc6), chr(0xc7), chr(0xc8),
          chr(0xc9), chr(0xca), chr(0xcb), chr(0xcc), 'SEG$', 'RPT$', 'POS', 'LEN',
          'VAL', 'NUMERIC', 'ASC', 'RND', 'PI', 'KEY$', 'CHR$', 'STR$', 'ABS', 'ACOS',
          'ASIN', 'ATN', 'COS', 'EXP', 'INT', 'ATANH', 'LN', 'LOG', 'SGN', 'SIN', 
          'SQR', 'TAN', 'EOF', 'FRE', 'SINH', 'COSH', 'TANH', 'ASINH', 'ACOSH', 
          'NULL', 'VALIDATE', '#', 'ALL', 'TAB', 'USING', 'INTERNAL', 'OUTPUT', 
          'UPDATE', 'APPEND', 'VARIABLE', 'SIZE', 'AT', 'REC', 'ERASE', 'RELATIVE', 
          chr(0xfe), chr(0xff)]
TOKENS_SPACES = ['01', '01', '01', '01', '00', '00', '01', '01', '01',
                 '01', '01', '01', '01', '01', '00', '01', '01',
                 '11', '11', '01', '01', '00', '00', '01', '00',
                 '00', '01', '01', '01', '01', '00', '00', '01', '01',
                 '01', '00', '00', '00', '00', '00', '00',
                 '11', '11', '11', '00', '00', '00', '11', '11', '11', '00', '00', '00',
                 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '01',
                 '00', '00', '00', '00', '00', '00', '00',
                 '00', '00', '00', '00', '00', '00', '00', '00',
                 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00',
                 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00',
                 '00', '00', '00', '00', '00', '00', '00', '00', '00',
                 '00', '00', '00', '01', '01', '01', '00', '00',
                 '00', '00', '01', '00', '00', '01', '11', '01',
                 '00', '00']
# Extended TOKENS formed by two bytes, the first one is the fixed character 0x80 and the 
# second one count from 0x40 to 0x4F (0x10 tokens).
EXTENDED_TOKENS = ['RUN', 'DELETE', 'FORMAT', 'BREAK', 'UNBREAK', 'DEG', 'RAD', 'GRAD',
                   'WARNING', 'ERROR', 'PROTECTED', 'DIGIT', 'UALPHANUM', 'UALPHA',
                   'ALPHANUM', 'ALPHA']
EXTENDED_TOKENS_SPACES = ['00', '00', '00', '01', '00', '00', '00', '00',
                          '00', '01', '00', '00', '00', '00',
                          '00', '00']
ERROR_MSG = {  1: 'Unexpected symbol at the end of syncro block.',
               2: 'Syncro Block has not end.',
               3: 'Syncro block shorter then exepected.',
              10: 'CheckSum Error: SECTION 1, FIRST BLOCK.',
              11: 'Unexpected symbol at the end of the block: SECTION 1, FIRST BLOCK.',
              12: 'Name len higher than maximun: SECTION 1, FIRST BLOCK',
              13: 'Insufficient numbre of data:  SECTION 1, FIRST BLOCK.',
              20: 'CheckSum Error: SECTION 1, SECOND BLOCK.',
              21: 'Unexpected symbol at the end of the block: SECTION 1, SECOND BLOCK.',
              23: 'Insufficient numbre of data:  SECTION 1, SECOND BLOCK.',
              30: 'CheckSum Error: SECTION 3, PROGRAM CODE ID BLOCK.',
              31: 'Unexpected symbol at the end of the block: PROGRAM CODE ID BLOCK.',
              33: 'Insufficient numbre of data:  SECTION 3, ID BLOCK.',
              40: 'CheckSum Error: SECTION 3, PROGRAM CODE BLOCK.',
              41: 'Unexpected symbol at the end of the block: FOURTH BLOCK.',
              43: 'Insufficient numbre of data:  SECTION 3, CODE BLOCK.',
              90: 'Insufficient number of SECTIONS.',
             100: 'No DATA: LOAD or CREATE a new data file first.',
             101: 'No DATA read from Arduino. Try again.',
             102: 'Communication ERROR: unplug arduino and restart programme',
             999: 'Any other else. Example do not continue the execution.'}

''' CONSTANT FOR TESTING PURPOSE'''
# PATH = "C:/a/My Python/Mi python/TI-74_Ejemplos/Examples/"
PATH = "./Examples/"


''' =========================
    =    GENERAL ROTINES    =
    ========================='''
def Calc_CheckSum (data):
    ''' Calculate the CheckSum of a byte object '''
    CheckSum = 0
    for i in range(len(data)):
        CheckSum +=data[i]
    return CheckSum_LB(CheckSum)

def CheckSum_LB (CheckSum):
    ''' Funcion to keep only the Low byte in the checksum value only'''
    if CheckSum > 255:
        CheckSum = CheckSum % 256
    return CheckSum

def Syncro_Block(Datos, Posicion ,ID, numero, ID_end):
    ''' To identify the syncronization block, ussually 1208 bytes containing 0x00 all of them
        ENTER:
        Datos: array of bytes containing the data to analyze
        Posicion: Integer, indcates the start index  to identify he block
        ID: byte, the byte 
        numero: the maximun number of time which appears ID  
        ID_end: byte, the byte identification of the block ends 

        RETURN:
        The number of bytes contaning the ID
    '''
    offset = 0
    to_swift = 0 
    if Posicion<len(Datos):
        dato = ID
        while dato == ID and offset<numero:
            offset += 1
            if Posicion + offset >= len(Datos)-1:
                return 2, offset, to_swift            
            if offset < MIN_SYNCRO_ZERO:
                dato = ID
            else:
                dato = Datos[Posicion+offset]
        if offset < numero:
            if dato == ID_end:
                return 0, offset, to_swift
            elif dato == 0x7f: # 01111111
                if Datos[Posicion+offset+1] & 0x80 == 0x80: # 10000000
                    to_swift = 1
                else:
                    return 1, offset, to_swift
            elif dato == 0x3f: # 00111111
                if Datos[Posicion+offset+1] & 0xc0 == 0xc0: # 11000000
                    to_swift = 2
                else:
                    return 1, offset, to_swift
            elif dato == 0x1f: # 000111111
                if Datos[Posicion+offset+1] & 0xe0 == 0xe0: # 11100000
                    to_swift = 3
                else:
                    return 1, offset, to_swift
            elif dato == 0x0f: # 00001111
                if Datos[Posicion+offset+1] & 0xf0 == 0xf0: # 11110000
                    to_swift = 4
                else:
                    return 1, offset, to_swift
            elif dato == 0x07: # 00000111
                if Datos[Posicion+offset+1] & 0xf8 == 0xf8: # 11111000
                    to_swift = 5
                else:
                    return 1, offset, to_swift
            elif dato == 0x03: # 0000000011 
                if Datos[Posicion+offset+1] & 0xfc == 0xfc: # 11111100
                    to_swift = 6
                else:
                    return 1, offset, to_swift
            elif dato == 0x01: # 00000001
                if Datos[Posicion+offset+1] & 0xfe == 0xfe: # 11111110
                    to_swift = 7
                else:
                    return 1, offset, to_swift
            else:
                return 1, offset, to_swift
        else:
            return 2, offset, to_swift
    else:
        return 3, 0, to_swift
    return 0, offset, to_swift

def dato_shift (dato1, dato2, to_shift):
    if to_shift != 0:
        uno=(dato1 << to_shift).to_bytes(2,'little')[0]
        return uno + (dato2 >> (8-to_shift))
    else:
        return dato1

def First_Block(Datos, Posicion, to_shift=0, Repeticion=True):
    '''SECCION IDENTIFICADOR NOMBRE:
    - Bloque ID
      0x00 0xZZ 0x00 0x00 0xZZ 0x84 0xSU --> ZZ numero de datos del bloque sección nombre (no incluye el CheckSum).
                                             SU CheckSum del bloque de datos.
      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
      Repetición bloque e indicación de fin de bloque.
    '''

    datos_pendientes = len(Datos) - Posicion
    if to_shift == 0:
        add_one = 0
    else:
        add_one = 1
    if Repeticion:
        minimo_datos = SECTION1_BLOCK1_NUM_DATA *2 + add_one
    else:
        minimo_datos = SECTION1_BLOCK1_NUM_DATA + add_one
    if datos_pendientes >= minimo_datos:
        offset = 6
        CheckSum=0
        NextPosicion = Posicion + offset
        LargoNombreArchivo=dato_shift(Datos[Posicion+1],Datos[Posicion+2], to_shift)-OFFSET_NAME
        while Posicion<NextPosicion:
            CheckSum += dato_shift(Datos[Posicion], Datos[Posicion+1], to_shift)
            Posicion += 1
        # CheckSum verification
        CheckSum = CheckSum_LB(CheckSum)
        File_CheckSum=dato_shift(Datos[Posicion], Datos[Posicion+1], to_shift)
        if File_CheckSum != CheckSum:
            # Try the Backup Copy
            if Repeticion:
                Posicion += CS + BU + ES
                return First_Block(Datos, Posicion, to_shift , False)
            Posicion += CS + BU + ES 
            return 10, Posicion, LargoNombreArchivo, CheckSum
        else:
            if Repeticion:
                Posicion += CS + BU + ES + offset + CS + BU + ES
            else:
                Posicion += CS + BU + ES
            if LargoNombreArchivo > MAX_LEN_FILE_NAME + 3: # Len of file name > MAX_LEN_FILE_NAME
                return 12, Posicion, LargoNombreArchivo, CheckSum
            else:
                return 0, Posicion, LargoNombreArchivo, CheckSum
    else: # Insuffient data
        return 13, Posicion, 0, 0           

def Second_Block(Datos, Posicion, LargoNombreArchivo, to_shift=0, Repeticion=True):
    '''SECCION IDENTIFICADOR NOMBRE:
    - Bloque nombre
      0xHH 0xGG 0x80 0xII ... 0xYY 0xSU  --> GGHH (Word) Número total de datos (bloque programa+bloque variables). Orden inverso LB+HB.
                                             II ... YY Caracteres ASCII del Nombre de archivo.
                                             SU CheckSum del bloque.
      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
      Repetición bloque, NO se repite la indicación de fin de bloque.
      0xFF'''

    datos_pendientes = len(Datos) - Posicion
    if to_shift == 0:
        add_one = 0
    else:
        add_one = 1
    if Repeticion:
        minimo_datos = (SECTION1_BLOCK2_NUM_DATA + LargoNombreArchivo) * 2 + BU + add_one
    else:
        minimo_datos = SECTION1_BLOCK2_NUM_DATA + LargoNombreArchivo + add_one
    if datos_pendientes >= minimo_datos:
        offset = OFFSET_NAME
        TotalDatos=(dato_shift(Datos[Posicion+1],Datos[Posicion+2],to_shift)<<8)+dato_shift(Datos[Posicion],Datos[Posicion+1],to_shift)
        CheckSum=dato_shift(Datos[Posicion],Datos[Posicion+1],to_shift)+\
                 dato_shift(Datos[Posicion+1],Datos[Posicion+2],to_shift)+\
                 dato_shift(Datos[Posicion+2],Datos[Posicion+3],to_shift)
        Posicion += offset
        NextPosicion = Posicion + LargoNombreArchivo
        NombreArchivo=""
        while Posicion < NextPosicion:
            CheckSum += dato_shift(Datos[Posicion],Datos[Posicion+1],to_shift)
            NombreArchivo += chr(dato_shift(Datos[Posicion],Datos[Posicion+1],to_shift))
            Posicion += 1
            offset += 1
        # CheckSum Verification
        CheckSum = CheckSum_LB(CheckSum)
        File_CheckSum=dato_shift(Datos[Posicion],Datos[Posicion+1],to_shift)
        if File_CheckSum != CheckSum:
            # Try the Backup Copy
            if Repeticion:
                Posicion += CS + BU + ES
                return Second_Block(Datos, Posicion, LargoNombreArchivo , to_shift, False)
            Posicion += CS + ES
            return 20, Posicion, TotalDatos, NombreArchivo, CheckSum
        else:
            if Repeticion:
                Posicion += CS + BU + ES + offset + CS + ES
            else:
                Posicion += CS + ES
            return 0, Posicion, TotalDatos, NombreArchivo, CheckSum 
    else:  # Insuffient data
        return 23, Posicion,  0, '', 0           

def ProgramInfo_Block(Datos, Posicion, to_shift=0, Repeticion=True):
    '''SECCIÓN PROGRAMA.
    - Bloque identificador.
      0xGG 0xHH 0xII 0xJJ 0xKK 0x82 0xSU --> GGHH (Word) Número total de datos (bloque programa+bloque variables). 
                                             Contando a apartir de "a".
                                             IIJJ (Word) Número de bloques de 64 bytes de datos.
                                             KK Número de bytes del último bloque. 
                                             IIJJ x 40 + KK = GGHH         
      0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xFF --> Indicación fin de Bloque.
      Repetición bloque e indicación de fin de bloque.
    '''
    
    if to_shift == 0:
        add_one = 0
    else:
        add_one = 1
    datos_pendientes = len(Datos) - Posicion
    if Repeticion:
        minimo_datos = SECTION3_ID_NUM_DATA *2 + add_one
    else:
        minimo_datos = SECTION3_ID_NUM_DATA + add_one
    if datos_pendientes >= minimo_datos:
        Total_NumDatos = (dato_shift(Datos[Posicion],Datos[Posicion+1],to_shift)<<8) + dato_shift(Datos[Posicion+1],Datos[Posicion+2],to_shift)
        Total_Bloques64bits = (dato_shift(Datos[Posicion+2],Datos[Posicion+3],to_shift)<<8) + dato_shift(Datos[Posicion+3],Datos[Posicion+4],to_shift)
        Residuo_Bloque64bits = dato_shift(Datos[Posicion+4],Datos[Posicion+5],to_shift)
        if Residuo_Bloque64bits != 0:
            total_datos = (Total_NumDatos + (CS+BU+ES)*(Total_Bloques64bits+1))*2-BU
        else:
            total_datos = (Total_NumDatos + (CS+BU+ES)*(Total_Bloques64bits))*2-BU
        if datos_pendientes >= minimo_datos + total_datos + add_one:
            CheckSum = 0
            for i in range(6):
                CheckSum += dato_shift(Datos[Posicion + i],Datos[Posicion+i+1],to_shift)
            CheckSum = CheckSum_LB(CheckSum)
            offset = 6
            Posicion += offset
            # CheckSum verification
            File_CheckSum=dato_shift(Datos[Posicion],Datos[Posicion+1], to_shift)
            if File_CheckSum != CheckSum:
                # Try the Backup Copy
                if Repeticion:
                    Posicion += CS + BU + ES
                    return ProgramInfo_Block(Datos, Posicion, to_shift, False)
                Posicion += CS + BU + ES
                return 30, Posicion, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, CheckSum
            else:
                if Repeticion:
                    Posicion += CS + BU + ES + offset + CS + BU + ES
                else:
                    Posicion += CS + BU + ES
                return 0, Posicion, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, CheckSum
        else:
            return 43, Posicion, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, 0
    else:
        return 33, Posicion, 0, 0, 0, 0
            
def Verify_CheckSum (Datos, Posicion, Numdatos, Repeticion=True):
    CheckSum = 0
    DatosLeidos = 0
    cadena = b''
    for i in range(Numdatos):
        DatosLeidos += 1
        cadena += Datos[Posicion].to_bytes(1,'little')
        CheckSum += Datos[Posicion]
        #print ('Posición ',Posicion, ' = ', hex(data[Posicion]))
        Posicion += 1
    #Comprobamos el CheckSum
    if CheckSum > 255:
        CheckSum = CheckSum % 256
    File_CheckSum=Datos[Posicion]
    if File_CheckSum != CheckSum:
        # Try the Backup Copy
        if Repeticion:
            Posicion += CS + BU + ES
            return Verify_CheckSum(Datos, Posicion, Numdatos, False)
        Posicion += CS + BU + ES
        return True, Posicion, cadena, CheckSum
    else:
        if Repeticion:
            Posicion += CS + BU + ES + DatosLeidos + CS + BU + ES
        else:
            Posicion += CS + BU + ES
        return False, Posicion, cadena, CheckSum 

def Ctape_to_Cbasic (Datos, Posicion, bytes_Number=0, log_file=False, file=None):
    '''CONVERSIÓN DE LA INFORMACION DE CASSETTE A BASIC COMPRIMIDO.
    - ENTRY DATA:
        Datos: array of bytes containing the data to analyze
        Posicion: Integer, indicates the start index of the progamme block
        bytes_number: Not used. 

    - RETURN:
        An array with the Compressed revision of the Basic code'''

    # Datos básicos de identificación del bloque de código
    #if log_file:
    #    for i in Datos:
    #        file.write('\{:#x}'.format(i))
    #    file.write ('\n\n')
    # The new bytes array: cbasic
    cbasic=b''    
    Error, Posicion, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, CheckSum = ProgramInfo_Block (Datos, Posicion)
    if Error !=0: 
        if log_file:
            file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
            if Error % 10 == 0:
                file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, Datos[Posicion-CS-BU-ES]))
        return Error, Posicion, cbasic, CheckSum
    NumeroBloques = Total_Bloques64bits
    if Residuo_Bloque64bits !=0:
        NumeroBloques += 1
    for i in range(NumeroBloques):
        CheckSum = 0
        if i < Total_Bloques64bits:
            rango = 64
        else:
            rango = Residuo_Bloque64bits
        if log_file:
            file.write ("Code block number: {:3d} ---> ".format(i+1))
        Error, Posicion, cadena, CheckSum = Verify_CheckSum (Datos, Posicion, rango, True)
        if Error: 
            return 40, Posicion, cbasic, CheckSum
        if log_file:
            file.write ('ChekcSum = {:#X}\n'.format(CheckSum))
        cbasic += cadena
    # Revert back the last jumping 8 + 1 (position must be located on a 0xFF: End of File)
    Posicion = Posicion - BU - ES 
    # cbasic += Datos[Posicion].to_bytes(1,'little')
    return 0, Posicion, cbasic, CheckSum

def cbasic_to_basic (cbasic, log_file=False, file=None, remove_end=True):
    '''DECODING FROM COMPRESSED BASIC TO A FULL TEXT BASIC.
    - IN:
        cbasic: array with the cbasic code to decode
        echoe: print to screen what it is happening during the process.

    - RETURN:
        list: A text list with the code text per line at each list line
        list: A list with the variables names'''

    # 1.- Variable names identification:
    Posicion=2
    Var_Starts = (cbasic [Posicion+1]<<8) + cbasic [Posicion]+4
    if log_file:
        file.write ('VARIABLES:\n')
        file.write ('Start position of the variables sub-block: {:#X}\n'.format(Var_Starts))
    Posicion += 2
    Var_Posicion=Var_Starts
    Var_Free = cbasic[Var_Posicion]
    if log_file:
        file.write ("First variable free in the TI-74 system: {:#X}\n".format(Var_Free))
    Var_Posicion += 1
    Variables = list()
    Var_Num=-1
    while Var_Posicion<len(cbasic):
        Var_Lenght = cbasic[Var_Posicion]
        Var_Posicion += 1
        if Var_Lenght != 0 and Var_Lenght != 0xff:
            Var_Num += 1
            Var_Name=""
            for i in range(Var_Lenght):
                Var_Name = Var_Name + chr (cbasic[Var_Posicion] & 0x7f)
                Var_Posicion += 1
            Variables.append(Var_Name)
    # Revert the variable list order
    Variables.reverse()
    if log_file:
        file.write ('Variable number: {:d}\n'.format(Var_Num+1))
        file.write ('Variables names : {}\n'.format(Variables))
        file.write ("--------------------------------------------------------------------\n")
    # 2.- Decoding line by line the BASIC code.
    Posicion = 4
    Lineas=list()
    Lin_Num = -1

    while Posicion < Var_Starts:
        # Número de línea
        Texto = str((cbasic[Posicion+1]<<8) + cbasic[Posicion]) + " "
        # Minimum length 6 = 5 digits plus one space
        Texto = " "*(6-len(Texto)) + Texto
        Lin_Lenght = cbasic[Posicion+2]-1
        Posicion += 3
        Actual = Posicion
        # In case two variable are consecutive, it has to be separated by an space.
        variable = False        
        while Posicion-Actual < Lin_Lenght:
            ID = cbasic[Posicion]
            if ID in range(0x81,0xc2) or ID in range(0xcc, 0xff): # Standard token
                # Especial case for "ELSE". "REM & "!"  token, remove ":" separator
                if ID in [0x82, 0xa0, 0x9E]:
                    if Texto[-1] == ":":
                        if Texto[-2] != " ":
                            Texto = Texto[:-1] + " "
                        else:
                            Texto = Texto[:-1]
                if TOKENS_SPACES[ID-0x81][0] == '1' and not(Texto[-1]in [' ',':']):
                    Texto += ' '
                Texto += TOKENS[ID-0x81]
                if TOKENS_SPACES[ID-0x81][1] == '1':
                    Texto += ' '
                variable = False
            elif ID == 0x00 and Posicion-Actual != Lin_Lenght-1: # Introduce ":" as separator
                #If previous character is SPACE, then remove
                if len(Texto)>1 and Texto[-1]==' ':
                    Texto = Texto[:-1]
                Texto += ":"
                variable = False
            elif ID in range(0x20): # Do nothing....
                pass
            elif ID in range(0x20, 0x80): # Is a variable name...
                # If previous token was a variables, then add an SPACE
                if variable:
                    Texto += ' ' 
                Texto = Texto + Variables[ID - 0x20]
                variable = True
            elif ID == 0x80: # Extended token
                Posicion += 1
                if EXTENDED_TOKENS_SPACES[cbasic[Posicion]-0x40][0] == '1' and Texto[-1]!=' ':
                    Texto += ' '
                Texto = Texto + EXTENDED_TOKENS[cbasic[Posicion]-0x40]
                if EXTENDED_TOKENS_SPACES[cbasic[Posicion]-0x40][1] == '1':
                    Texto += ' '
                variable = False
            elif ID in range(0xc2, 0xc9): # Is a number BCD format
                Posicion +=1 
                exponente = 2 * cbasic[Posicion] - 0x7F
                Numero = ""
                digitos = (ID-0xc1) * 2
                Posicion_Exponente=1
                for i in range(ID-0xc1):
                    Posicion +=1 
                    digito1 = (cbasic[Posicion] & 0xf0)>>4
                    digito2 = (cbasic[Posicion] & 0x0f)
                    Numero = Numero + str(digito1)
                    Numero = Numero + str(digito2)

                # Optimizing the number representation figures, trying to eliminate the exponent "E"
                if Numero[0] == "0" and digitos > 1: # Remove the first digit if ZERO 
                    Numero = Numero[1:]
                    exponente -= 1
                    digitos -= 1
                if Numero [-1] == "0" and digitos > 1: # Remove the last digit if ZERO
                    Numero = Numero [:-1]
                    digitos -= 1
                if 0<exponente<14: # Remove the exponential 
                    Posicion_Exponente += exponente
                    exponente = 0
                    # Add zeros at the end
                    if Posicion_Exponente>digitos:
                        Numero += "0" * (Posicion_Exponente-digitos)
                if digitos-14<exponente<0: # Remove the exponential
                    # Add zeros at begining
                    Numero = "0" * -exponente + Numero
                    exponente = 0
                # Locate the decimal "coma"
                Numero = Numero [:Posicion_Exponente] + "." + Numero [Posicion_Exponente:]
                if Numero[-1] == ".":
                    Numero = Numero[:-1]
                # Write the number & exponential
                if exponente != 0:
                    Numero += 'E' + str(exponente)
                Texto += Numero 
                variable= False
            elif ID == 0xc9: # "Quoted String":
                Posicion += 1
                Str_Length = cbasic[Posicion]
                Texto = Texto + '"'
                for i in range(Str_Length):
                    Posicion += 1
                    Texto = Texto + chr(cbasic[Posicion])
                    if chr(cbasic[Posicion])=='"':
                        Texto = Texto + chr(cbasic[Posicion])

                Texto = Texto + '"'
                variable = False
            elif ID == 0xca: # String without quotes
                Posicion += 1
                Str_Length = cbasic[Posicion]
                for i in range(Str_Length):
                    Posicion += 1
                    Texto = Texto + chr(cbasic[Posicion])
                variable = False
            elif ID == 0xcb: # Binary number suchs a Line number
                Posicion += 1
                Texto += str((cbasic[Posicion+1]<<8) + cbasic[Posicion])
                Posicion += 1
                variable = False
            Posicion += 1
        # Append the new decoded line.
        if Texto != "":
            Lineas.append(Texto)
    if remove_end and Lineas[-1] == '32767 END':
        Lineas.pop()
        if log_file:
            file.write ('Removed last line: 32767 END\n')


    return Lineas, Variables

def GetString (cadena, separador=SEPARADOR):
    ''' TO GET THE INTIAL STRING TO BE DECODED, 
    - IN:
        cadena: the string to sepparate
        separador: a list with the sepparator characters, by default SEPARADOR 
        
    - RETURN
        the estring to decode, and
        the remainig string
        '''

    posicion = 0
    auxiliar = ''
    if len(cadena)>0:
        # Hasta que se encuentre un separador
        while  posicion<len(cadena) and not(cadena [posicion:posicion+1] in separador):
            auxiliar += cadena[posicion:posicion+1]
            posicion += 1

    return auxiliar, cadena [posicion:].lstrip()

def QuotedString (cadena):
    ''' TO IDENTIFY A QUOTED STRING
    -IN:
        cadena: the string to sepparate the quoted string, starting without QUOTE
    - RETURN
        the quoted string, and
        the reamining string.

    NOTE: inside the quoted string a double " means one " inside the string.
    '''
    # Buscamos el final de la cadena entre comillas. 
    i=0
    aux=''
    while i<len(cadena):
        if cadena[i] == '"':
            if i<len(cadena)-1 and cadena[i+1] =='"' :
                i += 1
                aux += '"'
            else:
                break
        else:
            aux += cadena[i]
        i += 1
    cadena = cadena [i+1:]
    return aux, cadena 

def IntegerNumber (numero):
    ''' CONVERT A INTEGER NUMBER (less than 65535) IN A TWO BYTE NUMBER 
    BUT LESS SIGNIFICANT FIRST AND HIGHT SIGNIFICANT SECOND (INVERSE ORDER) 
        - IN:
            Integer number to be converted
        - RETURN:
            byte string with the number
    '''
    try:
        valor=int (numero)
    except:
        valor=0
    
    return valor.to_bytes(2,'little')

def EncodingLine (linea, NewVar):
    ''' TO ENCODE A SIMPLE BASIC LINE
        - IN: 
            linea: An string withe the line to encode. Must include the line number
            NewVar: A list with the code variables
            
        - RETURN:
            error: Not yet used
            clinea: a byte string with the coded line
            NewVar: an updated code variable list.
    '''
    error = 0

    # Remove leading and tailing blanks 
    linea=linea.strip()

    # FIRST FIELD: line number
    numLinea, linea = GetString(linea)
    clinea=IntegerNumber(numLinea)
    #print (numLinea)
    codificado=b''
    elemento=0
    delimitator=False
    
    while len(linea)>0:
        inicio=0
        # Initial FILTERS
        if linea[0] == '"':
            delimitator=False
            # QUOTED TEXT
            codificado +=bytes.fromhex('c9')
            inicio=0
            texto, linea = QuotedString(linea[1:])
            # Text length
            codificado += len(texto).to_bytes(1,'little')
            # The text itself
            for i in range(len(texto)):
                codificado += ord(texto[i]).to_bytes(1,'little')
        elif linea[0] == "<":
            delimitator=False
            # ONE/TWO character token, but same starting
            inicio=1
            if len(linea) > 1:
                if linea[1] == ">":
                    inicio=2
                    codificado +=bytes.fromhex('b3') # <>
                elif linea[1] == "=":
                    inicio=2
                    codificado +=bytes.fromhex('b4') # <=
                else:
                    codificado +=bytes.fromhex('b7') # <
            else:
                codificado +=bytes.fromhex('b7') # <
        elif linea[0] == ">":
            delimitator=False
            # ONE/TWO charccters token
            inicio=1
            if len(linea) > 1 and linea[1] == "=":
                    inicio=2
                    codificado +=bytes.fromhex('b5') # >=
            else:
                codificado += bytes.fromhex('b8') # >
        elif (linea[0] not in ['!']) and (linea[0] in TOKENS):
            delimitator=False
            # ONE single character token
            inicio=1
            codificado +=(TOKENS.index(linea[0])+0x81).to_bytes(1,'little')
        elif linea[0] == ":":
            # DELIMITATOR,  separator between instructions
            inicio=1
            codificado +=bytes.fromhex('00')
            delimitator = True
        else:
            # To find the new token/word
            if (len(linea)>1) and (linea[0] in ['!']):
                # This a special token: !
                texto = linea[0]
                linea = linea[1:]
            else:
                texto, linea = GetString(linea)
            if texto == '':
                pass
            elif texto in ['REM', '!']:
                # Comment in BASIC
                # Must be 0x00 (separator) before when is second or more statement
                if len(codificado)>0 and not(delimitator):
                    codificado += bytes.fromhex('00')
                if texto =='REM':
                    codificado += bytes.fromhex('82')
                elif texto == '!':
                    codificado += bytes.fromhex('a0')
                codificado += bytes.fromhex('ca')
                # remaining text is UNQUOTED TEXT
                codificado += len(linea).to_bytes(1,'little')
                # The text itself
                for i in range(len(linea)):
                    codificado += ord(linea[i]).to_bytes(1,'little')
                    inicio += 1
            elif (texto in TOKENS) or (texto in EXTENDED_TOKENS):
                delimitator=False
                if texto == "ELSE":
                    # Required a separator before
                    codificado += bytes.fromhex('00')
                if texto in EXTENDED_TOKENS:
                    codificado += bytes.fromhex('80')
                    codificado +=(EXTENDED_TOKENS.index(texto)+0x40).to_bytes(1,'little')
                else:
                    codificado +=(TOKENS.index(texto)+0x81).to_bytes(1,'little')
                if texto in ['GOTO', 'GOSUB', 'BREAK', 'CONTINUE', 'DIM', 'AT', 'ERROR', 'RESTORE', 'RETURN', 'RUN', 'UNBREAK', 'THEN', 'ELSE', 'USING']:
                    # Maybe followed by number or set of integer numbers sepparated by comas
                    while True:
                        lineaOld=linea
                        saltoLinea, linea = GetString(linea)
                        if saltoLinea == ',':
                            codificado += bytes.fromhex('ad')
                        else:
                            try:
                                valor=int (saltoLinea)
                                codificado += bytes.fromhex('cb')
                                codificado += valor.to_bytes(2,'little')
                            except:
                                # Do not follows a number
                                linea = lineaOld
                                break
                elif texto in ['CALL', 'SUB']:
                    # Must follow a NON QUOTED text
                    texto, linea = GetString(linea)
                    codificado += bytes.fromhex('ca')
                    codificado += len(texto).to_bytes(1,'little')
                    # The text itself
                    for i in range(len(texto)):
                        codificado += ord(texto[i]).to_bytes(1,'little')

                elif texto == 'DATA':
                    # Must follow the data separated by comas
                    while linea != '':
                        if linea[0] == '"':
                            # Quoted string
                            texto, linea = QuotedString(linea[1:])
                            codificado += bytes.fromhex('c9')
                        elif linea[0] == ',':
                            # field separator
                            linea=linea[1:].lstrip()
                            texto = ","
                        else:
                            # get next field  
                            texto, linea = GetString(linea, [','])
                            codificado += bytes.fromhex('ca')
                        if texto == ',':
                            # field separator
                            codificado += bytes.fromhex('ad')
                        else:
                            # text lenght
                            codificado += len(texto).to_bytes(1,'little')
                            # The text itself
                            for i in range(len(texto)):
                                codificado += ord(texto[i]).to_bytes(1,'little')
                                
                elif texto == 'IMAGE':
                    # Must follow text till the line end, quoted or not quoted
                    if linea[0] == '"':
                        # Quoted string
                        texto, linea = QuotedString(linea[1:])
                        codificado +=bytes.fromhex('c9')
                    else:
                        # Non quoted string
                        texto = linea
                        linea = ''
                        codificado += bytes.fromhex('ca')
                    codificado += len(texto).to_bytes(1,'little')
                    # The text itself
                    for i in range(len(texto)):
                        codificado += ord(texto[i]).to_bytes(1,'little')


            else: # it is a variable or number
                if texto[0] in CARACTER_NUMERICOS and texto[0] != "E":
                    # NUMBER: Decimal point position
                    dec=0
                    exponente = 0
                    if texto[0] == '.':
                        texto = '0' + texto
                    try:
                        dec=texto.index('.')
                        texto=texto[0:dec]+texto[dec+1:]
                    except ValueError:
                        dec=len(texto)
                    # Remove leading and tailing ZEROS
                    while texto[0] == '0' and len(texto)>1:
                        texto=texto[1:]    
                        dec -= 1
                    while texto[len(texto)-1] == '0' and len(texto)>1:
                        texto=texto[:-1]    
                    if texto[len(texto)-1] == 'E':
                        if len(linea)>0 and linea[0] in ['+', '-']:
                            inicio = 1
                        else:
                            inicio = 0
                        while inicio<len(linea) and linea[inicio] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                            inicio += 1
                        exponente = int(linea[0:inicio])
                        texto = texto[:-1]
                    try:
                        posExp=texto.index('E')
                        exponente = int(texto[posExp+1:])
                        texto=texto[0:posExp]
                    except ValueError:
                        pass
                    exponente += dec - 1
                    if (exponente % 2) == 0:
                        exponente += 1
                        texto = '0' + texto
                    exponente = int((exponente+0x7F)/2)
                    if len(texto) % 2 != 0:
                        texto += '0'
                    codificado += (int(len(texto)/2) + 0xC1).to_bytes(1,'little')
                    codificado += exponente.to_bytes(1,'little')
                    if len(texto)>14:
                        texto = texto[0:14]
                    for i in range (0, len(texto),2):
                        codificado +=  bytes.fromhex(texto[i:i+2])
                else:
                    # VARIABLE: If variable does not exit, then add to the variable list.
                    if texto not in NewVar:
                        codificado +=(len(NewVar)+0x20).to_bytes(1,'little')
                        NewVar.append(texto)
                    else:
                        codificado +=(NewVar.index(texto)+0x20).to_bytes(1,'little')


        linea = linea [inicio:].lstrip()

    if codificado[-1] != bytes.fromhex('00'):
        clinea += (len(codificado)+2).to_bytes(1,'little') + codificado + bytes.fromhex('00')

    return clinea, NewVar

class TI75_Basic:
    def __init__ (self, name='name', cassette=b'',raw_cassette=b'', compressed_basic=b'',basic_text=list()):
        self.file_name = name.upper()         # The name of the file with path
        self.extension = ''
        self.path = '.'                       # Relative path
        self.cassette_full = cassette         # The complete CASSETTE data in format as binary object.
        self.cassette_section = raw_cassette  # The splitted CASSETTE data in a list of FOUR binary object.
        self.cbasic = compressed_basic        # The compressed BASIC code in format as binary object.
        self.basic_txt = basic_text           # The text BASIC basic code as a list of text lines.
        return

    def set_filename (self, path, name, extension):
        self.full_name = path + '/' + name
        self.file_name = name
        self.path = path
        self.extension = extension

    def set_cassette_full (self, cassette):
        self.cassette_full = cassette
        return

    def set_cassette_section (self, raw_cassette):
        self.cassette_section = raw_cassette
        return

    def set_cbasic (self, compressed_basic):
        self.cbasic = compressed_basic
        return

    def set_basic (self, basic_text):
        self.basic_txt = basic_text
        return

    def get_cassette_full (self):
        return self.cassette_full

    def get_cassette_section (self):
        return self.cassette_section

    def get_cbasic (self):
        return self.cbasic

    def get_basic (self):
        return self.basic_txt

    def cassette_full_shifted (self, pos_ini, pos_fin, to_shift):
        aux_list = b''
        if to_shift == 0:
            aux_list = self.cassette_full[pos_ini:pos_fin]
        else:
            for i in range(pos_ini, pos_fin):
                aux_list += dato_shift (self.cassette_full[i], self.cassette_full[i+1], to_shift).to_bytes(1,'little')
        return aux_list

    def cassette_full_to_cassette_section (self, log_file=False, file=None):
        '''Splits the full cassette data to the different sections of the wave data. Each section of the wave
        is a byte string ending with the character 0xff.
        '''
        self.cassette_section=list()
        if log_file:
            file.write ('CONVERSION FROM RAW CASSETTE FULL TO RAW CASSETTE SECTION\n\n')
            file.write ('File: {:s}.{:s}\n\n'.format(self.file_name, self.extension)) 
            file.write ("Analysis of the data: \n\n")
            file.write (' **** First Syncro block..... ---> ')
        #====================================================================================================
        # FIRST SYNCRO BLOCK
        offset = 0
        Error, offset, to_shift = Syncro_Block(self.cassette_full, offset, SYNCRO_BYTE, MAX_SYNCRO_DATA, BLOCK_END_ID)
        if Error !=0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
            return Error, ''
        # Intial position
        if log_file:
            file.write ('OK. Shifting bits to left: {:d}\n'.format(to_shift))
        position = offset + ES
        #====================================================================================================
        # SECTION 1, BLOCK 1: INITIAL SEGMENT
        if log_file:
            file.write (' -SECTION 1, FIRST BLOCK:\n')
            file.write ('Reading first block..... ---> ')
        position_ini = position
        Error, position, long_file_name, CheckSum = First_Block (self.cassette_full, position, to_shift, True)
        if Error !=0 :
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_full[position+offset+CS]))
            return Error, ''
        if log_file:
            file.write ('OK\n')
        #====================================================================================================
        # SECTION 1, BLOCK 2: FILE NAME & TOTAL NUMBER OF DATA
        if log_file:
            file.write ('- SECTION 1, SECOND BLOCK:\n')
            file.write ('Reading second block, file name and total number of data..... ---> ')
        Error, position, TotalDatos, NombreArchivo, CheckSum = Second_Block (self.cassette_full, position, long_file_name, to_shift, True)
        if Error != 0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_full[position+offset+CS]))
            return Error, ''
        # Add the FIRST SECTION to the list
        self.cassette_section.append(self.cassette_full_shifted(position_ini, position, to_shift))
        if log_file:
            file.write ('OK\n')
            file.write ('Total number of data bytes: {:#X}\n'.format(TotalDatos))
            file.write ('In tape file name: {:s}\n'.format(NombreArchivo))
        #====================================================================================================
        # SECOND SYNCRO BLOCK
        if log_file:
            file.write (' **** Second Syncro block..... ---> ')        
        Error, offset, to_shift = Syncro_Block(self.cassette_full, position, 0x00, 1500, 0xff)
        if Error !=0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
            return Error, ''
        # Intial position
        if log_file:
            file.write ('OK. Shifting bits to left: {:d}\n'.format(to_shift))
        position += offset + ES
        #====================================================================================================
        # SECTION 2, BLOCK 3:No sense block: 6 + 1 + 8 + 1 + 6 + 1 + 1
        position_ini = position        
        position += 6 + CS + BU + ES + 6 + CS + ES
        # Add the SECOND SECTION to the list
        self.cassette_section.append(self.cassette_full_shifted(position_ini, position, to_shift))
        #====================================================================================================
        # THIRD SYNCRO BLOCK
        if log_file:
            file.write (' **** Third Syncro block..... ---> ')
        Error, offset, to_shift = Syncro_Block(self.cassette_full, position, 0x00, 1500, 0xff)
        if Error !=0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
            return Error, ''
        # Intial position
        if log_file:
            file.write ('OK. Shifting bits to left: {:d}\n'.format(to_shift))
        position += offset + ES
        #====================================================================================================
        # SECTION 3, BLOCK 4: PROGRAM
        if log_file:
            file.write (' - SECTION 3, PROGRAM & VARIABLES\n')            
            file.write ('Reading data size and distribution..... ---> ')
        position_ini = position   
        # No queremos cambiar la posición del bloque. 
        Error, position, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, CheckSum = ProgramInfo_Block (self.cassette_full, position, to_shift)
        if Error != 0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_full[position+offset+CS]))
            return Error, ''
        if log_file:
            file.write ('OK\n')
            file.write ('Number total of data bytes: {:#X}\n'.format(Total_NumDatos))
            file.write ('Number of 64 bytes data blocks: {:#X}\n'.format(Total_Bloques64bits))
            file.write ('Remainder data bytes in the last data block, less than 64 bytes: {:#X}\n\n'.format(Residuo_Bloque64bits))
        if Residuo_Bloque64bits != 0:
            Total_Bloques = (Total_Bloques64bits+1)*2
        else:
            Total_Bloques = (Total_Bloques64bits)*2
        position += int(Total_NumDatos*2 + (Total_Bloques -1)*(CS + BU + ES) + CS + ES)
        # Add the THIRD SECTION to the list
        self.cassette_section.append(self.cassette_full_shifted(position_ini,position,to_shift))
        #====================================================================================================
        # FOURTH SYNCRO BLOCK
        if log_file:
            file.write (' **** Fourth Syncro block..... ---> ')
        Error, offset, to_shift = Syncro_Block(self.cassette_full, position, 0x00, 1500, 0xff)
        if Error !=0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
            return Error, ''
        # Intial position
        if log_file:
            file.write ('OK. Shifting bits to left: {:d}\n\n'.format(to_shift))
        position += offset + ES
        #====================================================================================================
        # SECTION 4, BLOCK 5:No sense block: 6 + 1 + 8 + 1 + 6 + 1 + 1
        position_ini = position
        position += 6 + CS + BU + ES + 6 + CS + ES
        # Add the SECOND SECTION to the list
        self.cassette_section.append(self.cassette_full_shifted(position_ini,position,to_shift))        
        #====================================================================================================

        if log_file:
            file.write ('CONVERTED DATA:\n')
            file.write ('===============\n\n')
            for i in range(len(self.cassette_section)):
                file.write ('Section #{:d}\n'.format(i+1))
                file.write ('{:s}\n\n'.format(str(self.cassette_section[i])))
            file.write ('\n')
        #f_basic = open ('./Examples/viejo_casic.74', 'wb')
        #f_basic.write(self.cassette_section[2])
        #f_basic.close()

        return 0, NombreArchivo

    def cassette_section_to_cbasic(self,  log_file=False, file=None):
        ''' Convert the RAW file (splited in sections) to a COMPRESSED basic file'''
        #====================================================================================================
        # SECTION 1, BLOCK 1: LENGTH OF THE FILE NAME (NEXT BLOCK)
        if log_file:
            file.write ('CONVERSION FROM CASSETTE SECTION TO TI-74 COMPRESSED BASIC CODE\n\n')
            file.write ('File: {:s}.{:s}\n'.format(self.file_name, self.extension))
            file.write ('SECTION 1, FIRST BLOCK:\n')
            file.write ('Reading first block..... ---> ')
        Error, Offset, LengthFileName, CheckSum = First_Block (self.cassette_section[0], 0, 0, True)
        if Error !=0 :
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_section[0][Offset - CS - BU - ES]))
            return Error
        if log_file:
            file.write ('OK\n\n')
        #====================================================================================================
        # SECTION 1, BLOCK 2: FILE NAME & TOTAL NUMBER OF DATA
        if log_file:
            file.write ('SECTION 1, SECOND BLOCK:\n')
            file.write ('Reading second block, file name and total number of data..... ---> ')
        Error, Offset, TotalDatos, file_name, CheckSum = Second_Block (self.cassette_section[0], Offset, LengthFileName, 0, True)
        if Error != 0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_section[0][Offset - CS- ES]))
            return Error
        if log_file:
            file.write ('OK\n')
            file.write ('Total number of data bytes: {:#X}\n'.format(TotalDatos))
            file.write ('In tape file name: %s\n\n' % file_name)
        # TODO: Usar o no usar el nombre del archivo WAV
        #====================================================================================================
        # SECTION3, BLOCK 4: PROGRAM
        if log_file:
            file.write ('SECTION 3, PROGRAM CODE :\n')
            file.write ('Segment: PROGRAM SIZE & VARIABLES\n')
            file.write ('Reading data size and distribution..... ---> ')        
        Error, Pos, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, CheckSum = ProgramInfo_Block (self.cassette_section[2], 0)
        if Error != 0: 
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_section[2][Pos - CS - BU - ES]))
            return Error
        if log_file:        
            file.write ('OK\n')
            file.write ('Number total of data bytes: {:#X}\n'.format(Total_NumDatos))
            file.write ('Number of 64 bytes data blocks: {:#X}\n'.format(Total_Bloques64bits))
            file.write ('Remainder data bytes in the last data block, less than 64 bytes: {:#X}\n'.format(Residuo_Bloque64bits))
            file.write ("Segment: BASIC CODE:\n")        
        #====================================================================================================
        # Section program code itself. It must be grouped because if is grouped by segments of 0x40 bytes with its Backups.
        Error, Posicion, self.cbasic, CheckSum=Ctape_to_Cbasic (self.cassette_section[2], 0, log_file=log_file, file=file)
        if Error !=0:
            if log_file:
                file.write ('\nError: {:d} - {:s}\n'.format(Error, ERROR_MSG[Error]))
                if Error % 10 == 0:          
                    file.write ('CheckSum calculated: {:#X}, in the file (real one): {:#X}\n'.format(CheckSum, self.cassette_section[2][Posicion-CS-BU-ES]))                
            return Error
        if log_file:
            file.write ('Last position: {:#X}\n\n'.format(self.cassette_section[2][Posicion]))
            file.write ('Process ends.\n\n')
        return 0, file_name

    def cbasic_to_basic (self, log_file=False, file=None):
        # We are ready to decode to plain BASIC format.
        if log_file:
            file.write ('CONVERSION FROM TI-74 COMPRESSED BASIC CODE TO TEXT BASIC CODE\n\n')
            file.write ('File: {:s}.{:s}\n\n'.format(self.file_name, self.extension))        
        self.basic_txt = list()
        self.basic_variables = list()
        self.basic_txt, self.basic_variables = cbasic_to_basic (self.cbasic, log_file, file)
        if log_file:
            file.write ('\nDECODED CODE:\n')
            file.write ('=============\n')
            for i in range(len(self.basic_txt)):
                file.write ('{:s}\n'.format(self.basic_txt[i]))
            file.write ('\n')

    def basic_to_cbasic(self, log_file=False, file=None):
        ''' Convert based text BASIC as a list of lines to a Compressed Basic as a byte object
        '''
        if log_file:
            file.write ('CONVERSION FROM TEXT BASIC CODE TO TI-74 COMPRESSED BASIC CODE\n\n') 
            file.write ('File: {:s}.{:s}\n\n'.format(self.file_name, self.extension))        
        # Tray to compress the text file, line per line
        NewVariables=list()  # Variables list
        self.cbasic = b''          # The compressed code
        
        for i in range(len(self.basic_txt)):
            linea=self.basic_txt[i]
            clinea, NewVariables = EncodingLine (linea, NewVariables)
            self.cbasic += clinea
        # Adding the last line: 32767 END
        clinea, NewVariables = EncodingLine ('32767 END', NewVariables)
        self.cbasic += clinea
        if log_file:
            file.write ('Added the last line: 32767 END\n\n') 

        # Add the token of definition of program and size of the code.
        self.cbasic = bytes.fromhex('80') + bytes.fromhex('03') + int(len(self.cbasic)).to_bytes(2,'little') + self.cbasic


        # Variables section: invert the order of the variables list.
        NewVariables.reverse()
        
        clinea = b'' # Variables bytes definition
        clinea +=(len(NewVariables)+0x20).to_bytes(1,'little') # First variable number free in the TI-75


        for var in NewVariables:
            clinea +=(len(var)).to_bytes(1,'little') # Variable name length
            for i in range (len(var)-1):
                clinea += ord(var[i]).to_bytes(1,'little') # Upload all variable name except the last one.
            
            clinea += (ord(var[len(var)-1]) | 0x80).to_bytes(1,'little') # Last variable name character, the first bit is to set ONE.
        clinea += bytes.fromhex('00')
        # The cbasic has not token END of section 0xff
        #clinea += bytes.fromhex('ff')  

        # Join program code section with the variable section
        self.cbasic += clinea

        if log_file:
            file.write ('Process ends\n\n')         

        return

    def cbasic_to_cassette_section (self, log_file=False, file=None):
        ''' Convert the cbasic code to a raw per sections code, to be ready for a wave conversion.
        '''
        self.cassette_section=list()
        if log_file:
            file.write ('CONVERSION FROM TI-74 COMPRESSED BASIC CODE TO RAW CASSETTE SECTION\n\n')   
            file.write ('File: {:s}.{:s}\n\n'.format(self.file_name, self.extension))       
        # Normalize the file name to TI-74 standard
        new_name = self.file_name
        if new_name[0] in ['0','1','2','3','4','5','6','7','8','9']:
            new_name ='A'+ new_name
        new_name = new_name.replace (",", "") # Remove "," character
        new_name = new_name.replace (".", "") # Remove "." character
        if len(new_name) > 18:
            new_name=new_name[0:18]

        # Frist block....
        CheckSum = CheckSum_LB(2*(len(new_name)+3)+0x84)
        block = (bytes(1)) + (len(new_name)+3).to_bytes(1,'little') + (bytes(2)) + (len(new_name)+3).to_bytes(1,'little') +\
                0x84.to_bytes(1,'little') + CheckSum.to_bytes(1,'little') + (bytes(8)) + 0xff.to_bytes(1,'little') 
        block += block
        sub_block = len(self.cbasic).to_bytes(2,'little') + 0x80.to_bytes(1,'little')

        for i in range(len(new_name)):
            sub_block += ord(new_name[i]).to_bytes(1,'little')
        CheckSum = Calc_CheckSum(sub_block) 
        sub_block += CheckSum.to_bytes(1,'little')           
        block += sub_block + (bytes(8)) + 0xff.to_bytes(1,'little') + sub_block + 0xff.to_bytes(1,'little')
        self.cassette_section.append(block)
        # Second block....
        self.cassette_section.append(SECTION_2)        
        # Third block, the code itself....
        number_64blocks = len(self.cbasic) // 64
        remainder = len(self.cbasic) % 64
        block = len(self.cbasic).to_bytes(2,'big') + number_64blocks.to_bytes(2,'big') + remainder.to_bytes(1,'little') + 0x82.to_bytes(1,'little') 
        CheckSum = Calc_CheckSum(block)
        block += CheckSum.to_bytes(1,'little') + (bytes(8)) + 0xff.to_bytes(1,'little') 
        block += block
        # Starts the program itself in block of 0x40 bytes...
        data=b''
        for i in range (number_64blocks):
            if data != b'':
                data +=  (bytes(8)) + 0xff.to_bytes(1,'little')
            sub_block=self.cbasic[i*64:(i+1)*64]
            CheckSum = Calc_CheckSum(sub_block)
            sub_block += CheckSum.to_bytes(1,'little')
            sub_block = sub_block + (bytes(8)) + 0xff.to_bytes(1,'little') + sub_block 
            data += sub_block
        if remainder != 0:
            if data != b'':
                data +=  (bytes(8)) + 0xff.to_bytes(1,'little')
            sub_block=self.cbasic[number_64blocks*64:]
            CheckSum = Calc_CheckSum(sub_block)
            sub_block += CheckSum.to_bytes(1,'little')
            sub_block = sub_block + (bytes(8)) + 0xff.to_bytes(1,'little') + sub_block 
            data += sub_block
        block += data + 0xff.to_bytes(1,'little')
        self.cassette_section.append(block)
        # Fourth block....
        self.cassette_section.append(SECTION_4)        

        if log_file:
            file.write ('CASSETTE NEW REVISION:\n')
            file.write ('======================\n\n')
            i=0
            for datos in self.cassette_section:
                file.write ('Section: {:d} ---> '.format(i))
                file.write ('{:s}\n\n'.format(str(datos)))
                i += 1
            file.write ('\n')

        #f_basic = open ('./Examples/Nuevo_cbasic.74', 'wb')
        #f_basic.write(self.cassette_section[2])
        #f_basic.close()

        if self.file_name != new_name:
            if log_file:
                file.write ('Name of the file normalized to TI-74 standard, from {:s} to {:s}\n\n'.format (self.file_name, new_name))
            return new_name        
        else:
            return self.file_name

    def cassette_section_to_cassette_full (self):
        self.cassette_full = b''
        for i in self.cassette_section:
            self.cassette_full += SYNCRO_BLOCK + i
        return
    
    def save_file_cassette_full (self):
        """
        Save to a file the COMPLETE CASSETTE data (includes the syncro section) to a file: Extension R74
        """
        cas_file = open (self.path+'/'+self.file_name+'.r74', 'wb')
        cas_file.write(self.get_cassette_full())
        cas_file.close()
        return

    def read_file_cassette_full (self):
        """
        Read a file the COMPLETE CASSETTE data (includes the syncro section): Extension R74
        """
        cas_file = open (self.path+'/'+self.file_name+'.r74', 'rb')
        self.cassette_full = cas_file.read()
        cas_file.close()
        return

    def save_cbasic (self):
        """
        Save to a file the COMPRESSED BASIC data (includes the syncro section) to a file: Extension C74
        """
        cas_file = open (self.path+'/'+self.file_name+'.c74', 'wb')
        cas_file.write(self.get_cbasic())
        cas_file.close()
        return

    def read_cbasic (self):
        """
        Read a file the COMPRESSED BASIC data: Extension B74
        """
        cbasic_file = open (self.path+'/'+self.file_name+'.c74', 'rb')
        self.cbasic = cbasic_file.read()
        cbasic_file.close()
        return

    def save_basic (self):
        """
        Save to a file the BASIC text data to a file: Extension BAS
        """
        basic_file = open (self.path +'/' + self.file_name+'.'+self.extension, 'w')
        for texto in self.basic_txt:
            basic_file.write(texto+"\n")
        basic_file.close()
        return

    def read_basic (self):
        """
        Read the BASIC text data to the variable: Extension BAS
        """
        basic_file = open (self.path +'/' + self.file_name+'.' + self.extension, 'r')
        for texto in basic_file:
            if texto[-1] == '\n':
                texto = texto[:-1]
            if texto != '':
                self.basic_txt.append(texto)
        basic_file.close()
        return


def main():

    cadena = '"Quote Test"'
    print (QuotedString(cadena[1:]))
    cadena = '"Quote""Test"'
    print (QuotedString(cadena[1:]))
    cadena = '"""Quote""""Test"""'
    print (QuotedString(cadena[1:]))

    # Open the binay file
    file_name = "./Examples/pepe.bin"
    #file_name = "largo_02.74"
    f = open (file_name, "rb")

    # Read data.
    data = f.read()

    print ("Analysis of the file: ", file_name)
    print ("")
    #====================================================================================================
    print ('First Syncro block.....', end=' ---> ')
    # FIRST SYNCRO BLOCK
    Error, offset, to_shift = Syncro_Block(data, 0, 0x00, 1500, 0xff)
    if Error:
        if offset > 0:
            print ('Error: End ID not found')
        else:
            print ('Error')
        sys.exit("First Syncro Block error")
    # Intial position
    print ('OK')
    Posicion = offset + ES
    #====================================================================================================
    # INITIAL SEGMENT
    print ('INITIAL SEGMENT:')
    print ('Reading Initial Segment.....', end=' ---> ')
    Error, Posicion, LargoNombreArchivo, CheckSum = First_Block (data, Posicion, to_shift, True)
    if Error: # Try to read the copy
        print ('CheckSum error, Calculated: ',hex(CheckSum), ', in the file, real one: ',hex(data[Posicion+offset+CS]))
        sys.exit("CheckSum error")
    print ('OK')
    #====================================================================================================
    # SECTION: FILE NAME & TOTAL NUMBER OF DATA
    print ("")
    print ('SEGMENT: FILE NAME AND TOTAL NUMBER OF DATA BYTES:')
    print ('Reading File name and lenght.....', end=' ---> ')
    Error, Posicion, TotalDatos, NombreArchivo, CheckSum = Second_Block (data, Posicion, LargoNombreArchivo, to_shift, True)
    if Error: # Try to read the copy
        print ('CheckSum error, Calculated: ',hex(CheckSum), ', in the file, real one: ',hex(data[Posicion+offset+CS]))
        sys.exit("CheckSum error")
    print ('OK')
    print ('Total number of data bytes: ', hex(TotalDatos))
    print ('File name: ', NombreArchivo)
    #====================================================================================================
    # SECOND SYNCRO BLOCK
    print ('Second Syncro block.....', end=' ---> ')
    Error, offset, to_shift = Syncro_Block(data, Posicion, 0x00, 1500, 0xff)
    if Error:
        if offset > 0:
            print ('Error: End ID not found')
        else:
            print ('Error')
        sys.exit("First Syncro Block error")
    print ('OK')
    Posicion += offset + ES
    #====================================================================================================
    # No sense block: 6 + 1 + 8 + 1 + 6 + 1 + 1
    Posicion += 6 + CS + BU + ES + 6 + CS + ES
    #====================================================================================================
    # THIRD SYNCRO BLOCK
    print ('Third Syncro block.....', end=' ---> ')
    Error, offset, to_shift = Syncro_Block(data, Posicion, 0x00, 1500, 0xff)
    if Error:
        if offset > 0:
            print ('Error: End ID not found')
        else:
            print ('Error')
        sys.exit("First Syncro Block error")
    print ('OK')
    Posicion += offset + ES
    #====================================================================================================
    # SECTION: PROGRAM
    print ("")
    print ('SEGMENT: PROGRAM & VARIABLES')
    print ('Reading data size and distribution.....', end=' ---> ')
    # No queremos cambiar la posición del bloque. 
    Error, Pos, Total_NumDatos, Total_Bloques64bits, Residuo_Bloque64bits, CheckSum = ProgramInfo_Block (data, Posicion, to_shift)
    if Error: # Try to read the copy
        print ('CheckSum error, Calculated: ',hex(CheckSum), ', in the file, real one: ',hex(data[Posicion+offset+CS]))
        sys.exit("CheckSum error")
    print ('OK')
    print ('Number total of data bytes: ', hex(Total_NumDatos))
    print ('Number of 64 bytes data blocks: ', hex(Total_Bloques64bits))
    print ('Remainder data bytes in the last data block, less than 64 bytes: ', hex(Residuo_Bloque64bits))
    #====================================================================================================
    # Section program code itself. It must be grouped because if is grouped by segments of 0x40 bytes with its Backups.
    print ('')
    print ("BLOCK: BASIC CODE")
    Error, Posicion, basic== (data, Posicion, 1)
    if Error != 0:
        print ('Error en el Checksum del CODE.')
    print ('Last position: ', hex(data[Posicion]))

    # Close the file
    f.close()


    # Create a new file just with the PROGRAM/VARIABLE section
    
    f_basic = open ('./Examples/Basic.74', 'wb')
    f_basic.write(basic)
    f_basic.close()




    file_name = input('File name to DECODE: ')
    file_input = PATH + file_name + ".C74"
    file_output = file_name+'.74'
    f_basic = open (file_input, "rb")
    basic = f_basic.read()
    f_basic.close()
    print ("")
    print ("--------------------------------------------------------------------")
    print ('Generating "Basic.74" file with the data in block: PROGRAM/VARIABLES')
    Lineas, Variables = cbasic_to_basic (basic, True)

    print ("")
    print ('DECODED CODE:')
    print ('=============')
    for i in range(len(Lineas)):
        print (Lineas[i])

    print ("")
    print ("")
    print ("--------------------------------------------------------------------")
    print ("------------------------- COMPRIMIENDO -----------------------------")
    print ("--------------------------------------------------------------------")
    print ('')

    # Ahora vamos a intentar codificarlo
    NewVariables=list()
    ccode = b''
    
    for i in range(len(Lineas)):
        linea=Lineas[i]
        clinea, NewVariables = EncodingLine (linea, NewVariables)
        ccode += clinea

    # Añadimos los códigos de definición de programa y su tamaño en bytes
    ccode = bytes.fromhex('80') + bytes.fromhex('03') + int(len(ccode)).to_bytes(2,'little') + ccode


    # Generamos la sección de variables, cambiamos el orden de las variables
    # Informamos si hay diferencias en el orden de las variables

    error= 0
    for i in range(len(NewVariables)):
        if NewVariables[i] in Variables:
            j = Variables.index(NewVariables[i])
            if i != j:
                error=1
                break
        else:
            error=2
            break
    if len(Variables) != len(NewVariables):
        print ('ERROR: NUMBER OF VARIBLES DO NOT MATCH')
    elif error==2:
        print ('VARIABLE NAMES DO NOT MATCH: ', NewVariables[i])
    elif error==1:
            print ('THE VARIABLES ORDER DOES NOT MATCH:')
            print ('Inital variables names: ', Variables)
            print ('')
            print ('Coded variable names  : ', NewVariables)
            print ('')
            print ('              NAME       OLD           NEW')
            print ('---------------------------------------------')
            for i in range(len(NewVariables)):
                if NewVariables[i] in Variables:
                    j = Variables.index(NewVariables[i])
                    if i != j:
                        print ('Variable: {:>10s}  {:#4X} ({:2d}) ---> {:#4X} ({:2d})'.format(NewVariables[i],(j+0x20),j,(i+0x20),i))
    else:
        print ('NO ERRORS IN THE VARIABLE SECTION')

    print ('')
    NewVariables.reverse()
    
    clinea = b''
    clinea +=(len(NewVariables)+0x20).to_bytes(1,'little')


    for var in NewVariables:
        clinea +=(len(var)).to_bytes(1,'little')
        for i in range (len(var)-1):
            clinea += ord(var[i]).to_bytes(1,'little')
        
        clinea += (ord(var[len(var)-1]) | 0x80).to_bytes(1,'little')
    clinea += bytes.fromhex('00')
    #clinea += bytes.fromhex('ff')

    # Se une el programa con las varibles
    ccode += clinea


    # Create a new file just with the PROGRAM/VARIABLE section
    f_basic = open (file_output, 'wb')
    f_basic.write(ccode)
    f_basic.close()
    


if __name__ == "__main__":
    main()
