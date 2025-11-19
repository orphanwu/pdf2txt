import time
from cnstd import LayoutAnalyzer
from PIL import Image
import numpy as np
import os
import io
import re
import sys
import shutil
import pdfplumber
import tesserocr
import Levenshtein

# pdfminer相关库
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage


# pdf转图片
def pdf2pic(path):
    pdf = pdfplumber.open(path)
    os.mkdir('./PatentPDF/pic')
    for m in range(len(pdf.pages)):
        page = pdf.pages[m]
        im = page.to_image(resolution=400)
        im.save('./PatentPDF/pic/' + str(m + 1) + '.png')
    pdf.close()


# 文本检测并切割成多张图片
# path是存放pdf图片的路径,crop 是存放切片图片的地方
def textDetection(path):
    count = 1
    cropPath = './PatentPDF/crop/'
    os.mkdir(cropPath)

    for img_fp in range(len(os.listdir(path))):

        analyzer = LayoutAnalyzer('layout')
        out = analyzer.analyze(path + '/' + str(img_fp + 1) + '.png', resized_shape=704)

        for i in range(len(out)):
            if out[i]['type'] == 'Text' and out[i]['score'] > 0.5:
                out[i]['box'][0] -= 30
                out[i]['box'][2] += 30
                row = tuple(np.concatenate((out[i]['box'][0], out[i]['box'][2]), axis=0))
                # print(row)
                img = Image.open(path + '/' + str(img_fp + 1) + '.png')
                img.crop(row).save(cropPath + str(count) + '.png', 'png')
                count += 1


# 对切割的图片进行 TesserOCR
# path是版面分析切割得到的图片
def detectedImgTesserOCR(path):
    text = ''
    for img_path in range(len(os.listdir(path))):
        img_name = str(img_path + 1) + '.png'
        try:
            image = Image.open(os.path.join(path, img_name))
            text += cleanOCR(tesserocr.image_to_text(image))
        except TypeError:
            continue
        text += '\n\n'
    return text


# 对pdf进行pdfminer解析
# pdf转换
def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    fp.close()
    device.close()
    retstr.close()
    return text


# 文本列表化
def Listlize(text):
    list = []
    for li in text.split('\n'):
        if len(li) > 4:
            list.append(li.strip())
    return list


# 寻找最相似的句子
def findMostSimilarSentence(line, miner):
    max_similarity = -1
    most_similarity_sentence = line

    for ref in miner:
        distance = Levenshtein.distance(line, ref)
        max_length = max(len(line), len(ref))
        similarity = 1 - distance / max_length

        if similarity > max_similarity:
            max_similarity = similarity
            most_similarity_sentence = ref

    if max_similarity >= 0.5 and 'cid' not in most_similarity_sentence:
        return most_similarity_sentence
    return line


# 清洗数据
def clean_txt(r):
    cleaned_txt = ''

    # 先进行文本格式规范，把中文格式字符转换为英文格式、删除一些乱码字符、规范化内容表示，degree 加点的各类信息
    r = r.replace('—', '-')
    r = r.replace('M )', 'M=')
    r = r.replace('Ł )', 'Ł=')
    r = r.replace('Ł', 'η')
    r = r.replace('¢ ¢', '\'\'')
    r = r.replace('¢', '\'')
    r = r.replace('i )', 'i=')
    r = r.replace('25)', '≈')
    r = r.replace('15)', '𝜖')
    r = r.replace('No.', 'No')
    r = r.replace('i.e.', 'i e ')
    r = r.replace('e.g. ', 'e g ')
    r = r.replace('e.g.', 'e g')
    r = r.replace('Fig.', 'Fig')
    r = r.replace('Figs.', 'Figs')
    r = r.replace('ref.', 'ref')
    r = r.replace('et al.', 'et al')

    r = r.replace('et. ', 'et ')
    r = r.replace('.𝜖', '.15)')
    r = r.replace('°C', 'degree C')  # 匹配摄氏度
    r = r.replace('°', ' degree')
    # 替换希腊字母
    r = r.replace('γ', 'gamma')
    r = r.replace('β', 'beta')
    r = r.replace('ε', 'epsilon')
    r = r.replace('α', 'alpha')
    r = r.replace('μ', 'mu')

    # 删掉奇怪的字符
    r = r.replace('‘', '')
    r = r.replace('´', '')
    r = r.replace('#', '')
    r = r.replace('⇑', '')
    r = r.replace('$', '')
    r = r.replace('Φ', '')
    r = r.replace('§', '')
    r = r.replace('£', '')
    r = r.replace('€', '')
    r = r.replace('…', '')
    r = r.replace('¥', '')
    r = r.replace('®', '')
    r = r.replace('_', '')
    r = r.replace('?', '')
    r = r.replace('«', '')
    r = r.replace('»', '')
    r = r.replace('@', '')
    r = r.replace('†', '')
    r = r.replace('‡', '')
    r = r.replace('□', '')
    r = r.replace('�', '')
    r = r.replace('ABSTRACT:', '')
    r = r.replace('A B S T R A C T', '')

    sentence_txt = ''
    # 按照\n分割文本，然后进行句子拼接
    for sentence in r.split('\n'):
        # 清洗每一行
        sentence = sentence.strip()
        if sentence.endswith('.'):
            sentence += ' '
        elif sentence.endswith('-'):
            sentence.rstrip('-')
        # 去除索引
        sentence = re.sub(r'\[\d+\]', '', sentence)
        sentence = re.sub(r'\[\d+(?:,\d+)*\]', '', sentence)
        sentence = re.sub(r'\[\d+–\d+\]', '', sentence)
        sentence = re.sub(r'\[\d+\s*–\s*\d+\]', '', sentence)
        sentence = re.sub(r'\[\d+(?:,\d+)*–\d+\]', ' ', sentence)
        sentence_txt = sentence_txt + ' ' + sentence

    # 按照. 大写字母进行分句
    sentence_txt = sentence_txt.replace('  ', ' ')
    sentence_txt = sentence_txt.replace('  ', ' ')
    sentence_txt = sentence_txt.replace('', '')
    sentence_txt = sentence_txt.replace('', '')
    sentence_txt = sentence_txt.replace('', '')
    sentence_txt = re.sub(r'([a-z]) \. ([A-Z])', r'\1.\n\2', sentence_txt)
    sentence_txt = re.sub(r'([a-z0-9])\. ([A-Z])', r'\1.\n\2', sentence_txt)
    sentence_txt = re.sub(r'(\))\. ([A-Z])', r'\1.\n\2', sentence_txt)
    sentence_txt = re.sub(r'(\) )\. ([A-Z])', r'\1.\n\2', sentence_txt)

    # 进行句子级清洗
    for sentence in sentence_txt.split('\n'):
        if len(sentence.split(' ')) < 5:
            continue
        if 'www.' in sentence:
            continue
        if 'http' in sentence:
            continue
        if 'DOI' in sentence:
            continue
        if "doi" in sentence:
            continue
        if "Beijing" in sentence:
            continue
        if "China" in sentence:
            continue
        if "Shanghai" in sentence:
            continue
        if "Zhang" in sentence:
            continue
        if "Liu" in sentence:
            continue
        if "Zhou" in sentence:
            continue
        if "License" in sentence:
            continue
        if 'license' in sentence:
            continue
        if 'licensed' in sentence:
            continue
        if 'conceived' in sentence:
            continue
        if 'paper' in sentence:
            continue
        if 'authors' in sentence:
            continue
        if 'University' in sentence:
            continue
        if 'Province' in sentence:
            continue
        if 'permission' in sentence:
            continue
        if 'review' in sentence:
            continue
        if 'Supervision' in sentence:
            continue
        if 'work' in sentence:
            continue
        if 'Cooperacion' in sentence:
            continue
        if 'supported by' in sentence:
            continue
        if 'E-mail' in sentence:
            continue
        if hasYear(sentence):
            continue
        if mostUpper(sentence):
            continue
        if mostSingeWord(sentence):
            continue

        cleaned_txt = cleaned_txt + sentence + '\n'
    return cleaned_txt


# 清洗OCR数据
def cleanOCR(text):
    if len(text) < 10:
        return ''
    if len(text.split(' ')) < 5:
        return ''
    if 'Received' in text:
        return ''
    if 'Published' in text:
        return ''
    if 'A R T I C L E I N F O' in text:
        return ''
    if 'References' in text:
        return ''

    return text


# 计算是不是大多数的单词是大写的，如果有超过40%的字符是大写，那肯定是无效的句子
def mostUpper(sentence):
    count = 0
    for char in sentence:
        if char.isupper():
            count += 1
    return True if count / len(sentence) > 0.4 else False


# 计算是不是超过30%的单词是少于三个字母的
def mostSingeWord(sentence):
    count = 0
    wordList = sentence.split(' ')
    for word in wordList:
        if len(word) < 3:
            count += 1
    return True if count / len(wordList) > 0.3 else False


# 判断一句话是否含有年份
def hasYear(sentence):
    match = re.search(r'\b(19|20)\d{2}\b', sentence)
    return match is not None


if __name__ == '__main__':
    # 保证一定传送参数了,而这里的额外参数只可能有一个
    if 1 == len(sys.argv):
        sys.exit(0)

    # 临时目录
    picTemp = './PatentPDF/pic/'
    cropTemp = './PatentPDF/crop/'

    # pdf转图片
    pdf2pic(sys.argv[1])
    # pdf图片文本检测
    textDetection(picTemp)

    # OCR解析，返回列表
    OCRContent = Listlize(detectedImgTesserOCR(cropTemp))
    # pdfminer解析，返回列表
    PDFMinerContent = Listlize(convert_pdf_to_txt(sys.argv[1]))

    # 相互检验
    finalTextList = []
    for line in OCRContent:
        finalTextList.append(findMostSimilarSentence(line, PDFMinerContent))

    # 列表转为文本
    text = ''
    for txt in finalTextList:
        text = text + txt + '\n'

    # 保存数据
    #with open(sys.argv[1].split('.pdf')[0] + ' final.txt', 'w', encoding='utf-8') as f:
    output_path = './PatentPDF' + sys.argv[1].split('.pdf')[0] + ' final.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(clean_txt(text))
        f.close()

    # 删除中间文件
    shutil.rmtree(picTemp)
    shutil.rmtree(cropTemp)
