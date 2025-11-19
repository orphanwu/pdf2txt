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
    r = r.replace('Fig.', 'Fig')
    r = r.replace('Figs.', 'Figs')
    r = r.replace('et al.', 'et al')
    r = r.replace('et. ', 'et ')
    r = r.replace('.𝜖', '.15)')
    r = r.replace('°C', 'degree C')  # 匹配摄氏度
    r = r.replace('°', ' degree')
    r = r.replace('(cid:1)C', 'degree C')
    r = r.replace('(cid:5)C', 'degree C')
    r = r.replace('(cid:1)', '-')
    r = r.replace('(cid:2)', '·')
    r = r.replace('(cid:3)', '≤')
    r = r.replace('(cid:4)', '·')
    r = re.sub(r'(cid:\d+)', '', r)
    # 删掉奇怪的字符
    r = r.replace('#', '')
    r = r.replace('⇑', '')
    r = r.replace('$', '')
    r = r.replace('Φ', '')
    r = r.replace('§', '')
    r = r.replace('£', '')
    r = r.replace('€', '')
    r = r.replace('¥', '')
    r = r.replace('®', '')
    r = r.replace('_', '')
    r = r.replace('?', '')
    r = r.replace('«', '')
    r = r.replace('@', '')
    r = r.replace('†', '')
    r = r.replace('‡', '')
    r = r.replace('ABSTRACT:', '')

    # 按照\n\n分割文本，par是一段段内容，因为训练是按照句子进行训练的，所以最终呈现句子的顺序有一定出入不要紧
    for par in r.split('\n\n'):

        # 结束标志（直接去除致谢和参考文献）
        if 'Acknowledgements' in par:
            break
        if 'ACKNOWLEDGMENTS' in par:
            break
        if 'References' in par:
            break
        if 'Reference' in par:
            break
        if 'REFERENCES' in par:
            break
        if 'R E F E R E N C E S' in par:
            break
        if 'REFERENCE' in par:
            break

        # 直接删除一些没有意义的段：段少于10个词(可能会误删一些文本，但为了整体的干净，这么做的收益是明显的)
        if len(par.split(' ')) < 10:
            continue

        # 将par原先\n分割的内容拼接起来
        concatedPar = ''
        for parline in par.split('\n'):
            if concatedPar.endswith('-'):
                concatedPar.rstrip('-')
                concatedPar += parline
            else:
                concatedPar = concatedPar + ' ' + parline
        # print(concatedPar.replace(". ",".\n"))

        # 处理句子级别信息
        concatedPar = concatedPar.replace(". ", ".\n")

        for sentence in concatedPar.split('\n'):
            # 对一些不需要对句子进行清除
            sentence = sentence.strip()
            sentence = sentence.replace('  ', ' ')
            # 去除索引
            sentence = re.sub(r'\[\d+\]', '', sentence)
            sentence = re.sub(r'\[\d+(?:,\d+)*\]', '', sentence)
            sentence = re.sub(r'\[\d+–\d+\]', '', sentence)
            sentence = re.sub(r'\[\d+\s*–\s*\d+\]', '', sentence)
            sentence = re.sub(r'\[\d+(?:,\d+)*–\d+\]', ' ', sentence)

            if len(sentence.split(' ')) < 10:  # 句子小于10个单词就丢掉
                continue
            if 'http' in sentence:
                continue
            if "www." in par:
                continue
            if "DOI" in sentence:
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
            if "Li" in sentence:
                continue
            if mostUpper(sentence):
                continue
            if mostSingeWord(sentence):
                continue

            cleaned_txt = cleaned_txt + sentence + '\n'

    return cleaned_txt


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


if __name__ == '__main__':

    pdfPath = './PatentPDF/Nascion_pdf/'
    txtPath = './PatentPDF/Nasicon_txt_origin/'
    # 逐一处理文献
    for pdf in os.listdir(pdfPath):
        start = time.time()
        r = convert_pdf_to_txt(pdfPath + pdf)
        with open(txtPath + pdf.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
            f.write(clean_txt(r))
            f.close()

        end = time.time()
        print(pdf, 'finished and use:', str(end - start))
