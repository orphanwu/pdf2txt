import shutil
# import tesserocr
import tesserocr
from PIL import Image
import re
import os
import pdfplumber
import sys

# pdf转图片
def pdf_pic(path):
    pdf = pdfplumber.open(path + '.pdf')
    os.mkdir(path)
    for i in range(len(pdf.pages)):
        page = pdf.pages[i]
        im = page.to_image(resolution=200)
        im.save(path + '/' + str(i + 1) + '.png')
    pdf.close()


# 数据清洗
def clean(r):
    flag = 0
    text = ''
    ref = ''
    for par in r.split('\n\n'):
        if flag == 0:
            if 'References' in par:
                flag = 1
            else:
                text += par
        else:
            ref += par
            ref += '\n\n'

    return clean_text(text) + '\n123456789\n' + clean_ref(ref)


def clean_text(r):
    # 文本替换
    r = r.replace(' y ', ' gamma ')
    r = r.replace(' y\n', ' gamma ')
    r = r.replace('y‘', "gamma'")
    r = r.replace('y/', 'gamma/')
    r = r.replace('y—', 'gamma-')
    r = r.replace('y;', "gamma'")
    r = r.replace('y phase', 'gamma phase')
    r = r.replace('No.', 'No')
    r = r.replace('i.e.', 'i e ')
    r = r.replace('e.g. ', 'e g ')
    r = r.replace('Fig.', 'Fig')
    r = r.replace('Figs.', 'Figs')
    r = r.replace('et al.', 'et al')
    r = r.replace('et. ', 'et ')
    r = r.replace('°C', 'degree C')  # 匹配摄氏度
    r = r.replace('°', ' degree')
    r = r.replace('\n\n', '||')
    r = r.replace('\n', ' ')  # 合并按照行识别的内容
    r = r.replace('||', '\n\n')
    r = r.replace('. ', '. \n\n')  # 按照. 分句
    r = r.replace('—', '-')
    r = r.replace(' um', ' μm')
    r = r.replace('(um)', '(μm)')
    r = r.replace('A B S T R A C T', '')
    r = r.replace('A R T I C L E I N F O', '')
    r = r.replace('A R T I C LE I NF', '')
    r = r.replace(':-', '×')
    r = r.replace('Ref.', 'Ref')
    r = r.replace('@', 'Φ')
    r = r.replace('®', 'Φ')
    r = r.replace('g: b', 'g·b')
    r = r.replace(' x ', '≠')
    r = r.replace('¢', 'c')
    r = r.replace('$', 'S')
    r = r.replace('‘', "'")

    # 换行处理
    q = ''
    for par in r.split('\n\n'):

        par = re.sub('- ', '', par)  # 处理被切分的单词
        par = re.sub('— ', '', par)  # 处理被切分的单词
        par = re.sub('-\n\n', '', par)
        par = re.sub('-\n', '', par)
        par = re.sub('\[[0-9]{1,2}\]', '', par)  # 删除[14]和[1]
        # par = re.sub('\[[0-9, ]+\]', '', par)       # 删除[14,16]
        par = re.sub('\[[0-9,]+-[0-9]+\]', '', par)  # 删除[14—16]和[14,17—19]

        if '®' in par:  # 这个有些多余
            continue
        if '©' in par:
            continue
        if '|' in par:
            continue
        if 'Materials Science' in par:
            continue
        if 'Acta ' in par:
            continue
        if '*' in par:
            continue
        if 'http' in par:
            continue
        if 'University' in par:
            continue
        if par[0:5] == ' ':
            continue
        if 'www.' in par:
            continue
        if 'Acknowledgement' in par:  # 直接将Acknowledgement,部分后面的内容给删除
            break
        if 'ACKNOWLEDGEMENTS' in par:
            break
        if len(par.split(' ')) > 5:
            if (par[-2] == '.' and par[-1] == ' ') or par[-1] == '.':
                q = q + par + '\n\n'
            else:
                q = q + par

    p = ''
    for par in q.split('\n\n'):  # 处理过长的句子，过长的句子一般都是图片表格识别出的内容
        if len(par.split(' ')) > 70:
            continue
        else:
            p = p + par + '\n\n'
    p = p.replace('\n\n', '\n')
    p = p.replace('\n\n', '')
    return p


def clean_ref(ref):
    q = ''
    for par in ref.split('\n\n'):
        par = re.sub('\[[0-9]{1,2}\]', '', par)
        if len(par) < 6:
            continue
        for line in par.split('\n'):
            q += line
        q += '\n\n'
    q = q.replace('\n\n', '\n')
    q = q.replace('\n\n', '')
    return q


if __name__ == '__main__':
    # 保证一定传送参数了,而这里的额外参数只可能有一个
    if 1 == len(sys.argv):
        sys.exit(0)

    # pdf转图片
    pdf_pic(sys.argv[1].split('.')[0])

    # 图片转 txt
    content1 = ''
    for i in range(len(os.listdir(sys.argv[1].split('.')[0] + '/'))):
        # sys.argv[j].split('.')[0]表示文件夹
        image = Image.open(sys.argv[1].split('.')[0] + '/' + str(i + 1) + '.png')
        content = tesserocr.image_to_text(image)
        content1 += content
    content1 = clean(content1)  # 清洗文本
    with open(sys.argv[1].split('.')[0] + ' final.txt', 'w', encoding='utf-8') as f:
        f.write(content1)
        f.close()
    # 删掉生成的图片
    # shutil.rmtree(sys.argv[1].split('.')[0])
