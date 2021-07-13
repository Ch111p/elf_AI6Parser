import lzss
import os
import struct

DEBUG=True

class ARCHeader:
    def __init__(self):
        self.fileOffset = 0
        self.fileSize = 0
        self.rawSize = 0
        self.fileName = ''
    
    def parseData(self, data=bytes):
        assert(len(data) == 0x110), 'Wrong arc head'

        tempName = ''
        for i in range(0x110 - 12):
            if (data[i] != 0):
                tempName += chr(data[i])
            else:
                for j in range(i):
                    self.fileName += chr(ord(tempName[j]) - i - 1 + j)
                break
        sizeData = data[-12:]
        self.fileSize = struct.unpack('>I', sizeData[:4])[0]
        self.rawSize = struct.unpack('>I', sizeData[4:8])[0]
        self.fileOffset = struct.unpack('>I', sizeData[8:12])[0]

    def print(self):
        print('FileName:%s, Size:0x%x, Offset:0x%x rawSize:0x%x' 
                %(self.fileName, 
                    self.fileSize, 
                    self.fileOffset, 
                    self.rawSize))

class ARCFile:
    def __init__(self, Path=''):
        self.path = Path
        self.headerNum = 0
        self.headers = []
        self.datas = []
    
    def parseFile(self):
        with open(self.path, 'rb') as fp:
            data = fp.read()
        
        self.headerNum = struct.unpack('<I', data[:4])[0]
        
        for i in range(self.headerNum):
            temp = ARCHeader()
            temp.parseData(data[4+i*0x110:4+(i+1)*0x110])
            if DEBUG == True:
                temp.print()
            self.headers.append(temp)
        
        for i in range(self.headerNum):
            self.datas.append(data[self.headers[i].fileOffset:
                self.headers[i].fileOffset + self.headers[i].fileSize])


    def decompressFile(self):
        os.mkdir(f'{self.path}_dec')
        for i in range(self.headerNum):
            with open(f'{self.path}_dec/{self.headers[i].fileName}', 'wb') as fp:
                print(f"Uncompress file{i}:{self.headers[i].fileName}")
                fp.write(lzss.decompress(self.datas[i]))
    
    def compressFile(self, path=str):
        for root, _, files in os.walk(path):
            for name in files:
                with open(f"{root}/{name}", 'rb') as fp:
                    tempData = fp.read()
                    tempHeader = ARCHeader()
                    tempHeader.fileName = name
                    tempHeader.rawSize = len(tempData)
                    compressData = lzss.compress(tempData)
                    tempHeader.fileSize = len(compressData)
                self.datas.append(compressData)
                self.headers.append(tempHeader)
                self.headerNum += 1
        fileData = bytearray()
        fileData += struct.pack("<I", self.headerNum)
        writedSize = 0

        for i in range(self.headerNum):
            strLength = len(self.headers[i].fileName)
            encryptedStr = "".join(chr((ord(self.headers[i].fileName[_]) + \
                strLength + 1 - _)) for _ in range(strLength)).ljust(0x110-12, '\x00')
            fileData += bytearray(encryptedStr.encode("latin1"))
            fileData += bytearray(struct.pack(">I", self.headers[i].fileSize))
            fileData += bytearray(struct.pack(">I", self.headers[i].rawSize))
            self.headers[i].fileOffset = 4+0x110*self.headerNum+writedSize
            fileData += bytearray(struct.pack(">I", self.headers[i].fileOffset))
            writedSize += self.headers[i].fileSize
            self.headers[i].print()
        
        for i in range(self.headerNum):
            fileData += bytearray(self.datas[i])

        with open(self.path, 'wb+') as fp:
            fp.write(fileData)

class MESFile:
    def __init__(self, Path=''):
        self.path = Path
        self.blockNum = 0 #seems like the first block is not counted in first blockNum
        self.offsets = []
        self.blocks = [] 
        self.texts = []
    
    def parseMESFile(self):
        def isShiftJS(nums):
            if (((nums[0] >= 0x81 and nums[0] <= 0x9f) or (nums[0] >= 0xe0 and nums[1] <= 0xef)) and \
                 ((nums[1] >= 0x40 and nums[1] <= 0x7e) or (nums[1] >= 0x80 and nums[1] <= 0xfc))):
                return True
            return False

        fileOffset = 0
        with open(self.path, 'rb') as fp:
            data = fp.read()

        self.blockNum = struct.unpack("<I", data[:4])[0]
        fileOffset += 4
        for _ in range(self.blockNum):
            self.offsets.append(struct.unpack("<I", data[fileOffset:fileOffset+4])[0])
            fileOffset += 4
        offset = 0
        for _ in range(self.blockNum):
            self.blocks.append(data[fileOffset:fileOffset+self.offsets[_]-offset])
            fileOffset += (self.offsets[_] - offset)
            offset = self.offsets[_]
        self.blocks.append(data[fileOffset:])

        for i in range(len(self.blocks)):
            strList = []
            j = 0
            while (j < len(self.blocks[i]) - 3):
                if self.blocks[i][j] == 0x0a and isShiftJS(self.blocks[i][j+1:j+3]):
                    j += 1
                    tempStr = []
                    try:
                        while(self.blocks[i][j] != 0):
                            tempStr.append(self.blocks[i][j])
                            j += 1
                    except:
                        print(self.path)
                        print(i, ' ', self.offsets[i - 1], ' ', j)
                    bytesA = bytearray(tempStr)
                    strList.append(bytesA)
                j += 1
            self.texts.append(strList)

    def rebuildFile(self):
        fileData = bytearray()
        fileData += struct.pack("<I", self.blockNum)
        for i in self.offsets:
            fileData += struct.pack("<I", i)
        for i in self.blocks:
            fileData += i
        with open(f"{self.path}_new", "wb+") as fp:
            fp.write(fileData)
        
    def refixJmp(self):
        return
        
    def replaceText(self, path=""):
        with open(path, "rb") as fp:
            lines = fp.readlines()

        bIndex = 0
        lineIndex = 0
        for i in range(len(lines)):
            if (lineIndex == len(self.texts[bIndex])):
                lineIndex = 0
                bIndex += 1
            if (len(lines[i]) % 2 == 1):
                lines[i] = lines[i][:-1]
            print(bIndex, lineIndex)
            print(self.texts[bIndex][lineIndex])
            print(lines[i])
            self.blocks[bIndex] = self.blocks[bIndex].replace(self.texts[bIndex][lineIndex], lines[i])
            offset = len(lines[i]) - len(self.texts[bIndex][lineIndex])
            if offset == 0:
                lineIndex += 1
                continue
            for i in range(bIndex, len(self.offsets)):
                self.offsets[i] += offset

            # fix JMP
            for j in range(bIndex, len(self.offsets) + 1):
                blockBegin = self.offsets[j - 1]
                blockEnd = blockBegin+len(self.blocks[j])
                start = 0
                if (j == bIndex):
                    start = self.blocks[j].find(lines[i]) + len(lines[i])
                k = start
                while k < len(self.blocks[j]) - 5:
                    if ((self.blocks[j][k] == 0x14 or self.blocks[j][k] == 0x15)):
                        offsetNum = struct.unpack(">I", self.blocks[j][k+1:k+5])[0]
                        assert(j != 0)
                        print(hex(offsetNum), hex(blockBegin), hex(blockEnd))
                        if (offsetNum >= blockBegin and offsetNum <= blockEnd):
                            self.blocks[j] = self.blocks[j][:k+1] + struct.pack(">I", offsetNum+offset) + self.blocks[j][k+5:]
                            k += 5
                        else:
                            k += 1
                    else:
                        k += 1
            lineIndex += 1
        
        self.rebuildFile()
    
    def extraText(self):
        with open(f'{self.path}.txt', 'wb+') as fp:
            for bText in self.texts:
                for text in bText:
                    fp.write(text.decode('cp932').encode("GBK") + b'\x0a')
        fp.close()


if __name__ == "__main__":
    for root, _, files in os.walk("./mes.arc~"):
        for name in files:
            if 'mes' in name:
                tempMES = MESFile(f"{root}/{name}")
                tempMES.parseMESFile()
                tempMES.extraText()
    # file1 = MESFile("./stage01.mes")
    # file1.parseMESFile()
    # file1.replaceText("./final.txt")
    # file1 = ARCFile("./temp.arc")
    # file1.compressFile("mes.arc_dec")
