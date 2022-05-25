# -*- coding: utf-8 -*-
"""Baseline_v1_0_augmented_by_songhee_nlpaug_speed_variation_2_disease_fin.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MopR_m-kamxQGYNSAOvjBRV6WNzew74K

<a href="https://colab.research.google.com/github/SongheeJo/aiffelthon/blob/main/Baseline_v1_0.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

1. **Load data**
    1. sampling rate 지정
        
        respireNet에서는 4kHz로 down sampling

    2. librosa.load 사용
    
    load 시 sampling rate 파라미터로 전체 data에 일괄 적용 가능

2. **Pre-processing**
    1. better SNR
        - `tfio.experimental.audio.trim()` tensorflow-io 패키지 노이즈 제거 ⇒ 들어보기
        - split & pad
            - 7초?
            - padding
              tfio.experimental.audio.fade tensorflow-io 패키지 페이딩 기술 ⇒ 현재 data에도 유용할까?
        - butterworth filter
            - `scipy.signal.butter()`

3. **Train_val_test_split**
    1. data imbalance 해결을 위해 파라미터 stratify 조정

4. **Augmentation**
    1. 일단 없이 진행 후 결과 보기
    2. 구현된 기본적인 augmentation 방법 적용해보고 결과 보기
        - 각 방법 별로 얼마나 결과가 좋아졌는지 저장 해둘 것
        - 각각 했을 때 vs 몇 개 같이 했을 때 결과 비교


5. **Feature Extraction**

6. **Build model**
   - transfer learning

7. **Evaluate**
    1. classification report text file 로 저장하는 module 생성
    2. recall 값과 f1 값

# 0. 추가사항

nlparg - speed variation (disease classification)

## 1. Load data
"""

from google.colab import drive
drive.mount('/content/drive')

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt
import seaborn as sns
import librosa.display
import soundfile as sf
import librosa as lb
import os

#root = '/content/drive/MyDrive/aiffel/aiffelthon/'
root = '/content/drive/MyDrive/'

"""###Data analysis (Disease)
crack & wheeze는 나중에

"""

diagnosis=pd.read_csv(root + 'Respiratory_Sound_Database/Respiratory_Sound_Database/patient_diagnosis.csv',names=['pid','disease'])
diagnosis.head()

# df=pd.read_csv(root + 'archive/Respiratory_Sound_Database/Respiratory_Sound_Database/audio_and_txt_files/160_1b3_Al_mc_AKGC417L.txt',sep='\t', names = ['start', 'end', 'crackles', 'weezels'])
# df.head()

# path=root + 'archive/Respiratory_Sound_Database/Respiratory_Sound_Database/audio_and_txt_files/'
path=root + 'Respiratory_Sound_Database/Respiratory_Sound_Database/audio_and_txt_files/'
files=[s.split('.')[0] for s in os.listdir(path) if '.txt' in s]
files[:5]

def getFilenameInfo(file):
    return file.split('_')

files_data=[]
for file in files:
    data=pd.read_csv(path + file + '.txt',sep='\t',names=['start','end','crackles','weezels'])
    name_data=getFilenameInfo(file)
    data['pid']=name_data[0]
    data['mode']=name_data[-2]
    data['filename']=file
    files_data.append(data)
files_df=pd.concat(files_data)
files_df.reset_index()
files_df.head()

df.info()

files_df.info()

"""두 데이터프레임을 merge하기 위해 같은 타입으로 통일해줍니다"""

df.pid=df.pid.astype('int32')
files_df.pid=files_df.pid.astype('int32')

sns.set_theme(style="darkgrid")
sns.countplot(df.disease)
plt.xticks(rotation=90)

data=pd.merge(files_df,diagnosis,on='pid')
data.head()

data.to_csv('/content/drive/MyDrive/csv_data/data.csv',index=False)

"""##2. Pre-processing

###Divide Data
데이터 자르면서 crack_wheeze가 포함된 새로운 컬럼을 만듭니다.
"""

def getPureSample(raw_data,start,end,sr=22050):
    
    '''
    Takes a numpy array and spilts its using start and end args
    
    raw_data=numpy array of audio sample
    start=time
    end=time
    sr=sampling_rate
    mode=mono/stereo
    '''

    max_ind = len(raw_data) #원본 데이터
    start_ind = min(int(start * sr), max_ind) #시작 시간 x sample rate
    end_ind = min(int(end * sr), max_ind)
    return raw_data[start_ind: end_ind]

i,c=0,0

filename2 = []
start2 = []
end2 = []
pid2 = []
mode2 = []
disease2 = []
crack_wheeze = []
for index,row in data.iterrows(): #enumerte 과 비슷
    start=row['start']
    end=row['end']
    filename=row['filename']
    
    audio_file_loc=path + filename + '.wav' #wav 파일 경로 저장
    
    if index > 0:
        #check if more cycles exits for same patient if so then add i to change filename
        if data.iloc[index-1]['filename']==filename:
            i+=1
        else:
            i=0
    filename= filename + '_' + str(i) + '.wav' #새로운 파일 이름

    filename2.append(filename)
    start2.append(row['start'])
    end2.append(row['end'])
    pid2.append(row['pid'])
    mode2.append(row['mode'])
    disease2.append(row['disease'])

    if row['crackles'] == 0 and row['weezels'] == 0:
      crack_wheeze.append(0)
    elif row['crackles'] == 1 and row['weezels'] == 0:
      crack_wheeze.append(1)
    elif row['crackles'] == 0 and row['weezels'] == 1:
      crack_wheeze.append(2)
    else:
      crack_wheeze.append(3)
    
    save_path='/content/drive/MyDrive/processed_audio_files_8/' + filename
    c+=1 #파일 개수 세기
    
    audioArr,sampleRate=lb.load(audio_file_loc, sr = 16000)
    pureSample=getPureSample(audioArr,start,end,sampleRate) #잘린 데이터 return, 길이는 상관 없음

    if c % 100 == 0:
      print(c)
    
    
    sf.write(file=save_path,data=pureSample,samplerate=sampleRate)
print('Total Files Processed: ',c)

processed = pd.DataFrame(columns=['start','end','pid','mode','filename','disease','crack_wheeze'])
processed['start'] = start2
processed['end'] = end2
processed['pid'] = pid2
processed['mode'] = mode2
processed['filename'] = filename2
processed['disease'] = disease2
processed['crack_wheeze'] = crack_wheeze

processed.to_csv(root + 'processed.csv')

processed = pd.read_csv(root + 'processed.csv') #우리가 계속 쓸 컬럼입니다

processed

"""원하는 길이로 패딩해서 wav로 저장합니다"""

sr=16000

def zero_padding(pureSample, reqLen = 7 * sr):
  padded = lb.util.pad_center(pureSample, reqLen)
  return padded

for index,row in processed.iterrows():
  maxLen=7 #5,6,7 선택
  start=row['start']
  end=row['end']
  filename=row['filename']
    
  audio_file_loc= root + 'processed_audio_files/' + filename #5,6,7 선택
  processed_sample, _ = lb.load(audio_file_loc, sr = sr) #자르고 전처리한 데이터

  #If len > maxLen , change it to maxLen
  if end-start>maxLen:
      end=start+maxLen
      processed_sample = processed_sample[int(start * sr) : int(end * sr)] #초에 맞춰주기
  
  padded_data = zero_padding(processed_sample,7 * sr)
  
  save_path = root + 'processed_audio_files_7sec_22050/' + filename

  sf.write(file=save_path,data=padded_data,samplerate = sr)

"""###butter worth filter()

##3. Train_val_test_split
"""

from sklearn.model_selection import train_test_split

Xtrain,Xval,ytrain,yval=train_test_split( #disease 분류
    processed,processed.disease,stratify=processed.disease,random_state=42,test_size=0.2)

Xtrain_1,Xval_1,ytrain_1,yval_1=train_test_split( #crack_wheeze 분류
    processed,processed.crack_wheeze,stratify=processed.crack_wheeze,random_state=42,test_size=0.2)

Xtrain

len(Xtrain)

ytrain

yval

Xtrain_1

"""disease 비율"""

Xtrain.disease.value_counts()/Xtrain.shape[0]

"""crackle & wheeze 비율"""

Xtrain_1.crack_wheeze.value_counts()/Xtrain_1.shape[0]

Xtrain.to_csv('train.csv')
Xval.to_csv('val.csv')

"""label 인코딩
- disease 라벨에만 적용 시킵니다
- crackle & wheeze 라벨은 이미 int로 되어있습니다
"""

from sklearn.preprocessing import LabelEncoder
le=LabelEncoder()
ytrain=le.fit_transform(ytrain)
yval=le.transform(yval)

ytrain

"""##4. Augmentation(추후 추가)

## nlpaug의 Audio Augmenter
"""

!pip install nlpaug

import nlpaug.augmenter.audio as naa
from nlpaug.util.audio.visualizer import AudioVisualizer

def getSounds(path):
    soundArr,sr=lb.load(path)
    return soundArr

root_path= root + 'processed_audio_files_7sec_22050/'
Xtrain_a=[]
for idx,row in Xtrain.iterrows():
    path=root_path + row['filename']
    c=getSounds(path)
    Xtrain_a.append(c)

Xtrain_array=np.array(Xtrain_a)

Xtrain_array

len(Xtrain_array)

Xtrain_array.shape

np.save(root + 'Xtrain_7sec.npy', Xtrain_array)

Xtrain_array = np.load('/content/drive/MyDrive/Xtrain_7sec.npy')

# ytrain_array=ytrain.values

"""### speed variation"""

# speed variation
aug_1 = naa.speed.SpeedAug(zone=(0.2, 0.8), coverage=1.0, factor=(0.5, 2), name='Speed_Aug', verbose=0, stateless=True) # coverage 개념이 와닿지 않음 - 1과 0, 0.5 비교해보고 zone과 coverage관계 살피기

augmented_data_speed_variation = []
type(augmented_data_speed_variation)

type(Xtrain_array[0])

aug_1.augment(Xtrain_array[0])

type(aug_1.augment(Xtrain_array[0]))

len(aug_1.augment(Xtrain_array[0]))

augmented_data_speed_variation = []
for i in range(len(Xtrain_array)): # 훈련 데이터 입력 
    x = aug_1.augment(Xtrain_array[i])
    augmented_data_speed_variation.append(x)
    i += 1

print(augmented_data_speed_variation)

len(augmented_data_speed_variation)

np.save(root + 'Xtrain_7sec_augmented_data_speed_variation.npy',augmented_data_speed_variation)

augmented_data_speed_variation = np.load('/content/drive/MyDrive/Xtrain_7sec_augmented_data_speed_variation.npy', allow_pickle=True)

Xtrain_array = augmented_data_speed_variation

"""### Random shifting"""

'''
# random shifting
aug_2 = naa.shift.ShiftAug(re_sampleRate, duration=3, direction='random', shift_direction='random', name='Shift_Aug', verbose=0, stateless=True) # direction과 shift_direction의 차이 찍어보기
augmented_data_random_shifting = aug_2.augment(Xtrain_2)
'''

'''
# random shifting (direction left)
aug_2_2 = naa.shift.ShiftAug(re_sampleRate, duration=3, direction='left', shift_direction='random', name='Shift_Aug_2', verbose=0, stateless=True)
augmented_data = aug_2_2.augment(Xtrain_2)
'''

'''
# random shifting (direction right)
aug_2_3 = naa.shift.ShiftAug(re_sampleRate, duration=3, direction='right', shift_direction='random', name='Shift_Aug_3', verbose=0, stateless=True)
augmented_data = aug_2_3.augment(Xtrain_2)
'''

"""### pitch"""

'''
# pitch
aug_3 = naa.pitch.PitchAug(re_sampleRate, zone=(0.2, 0.8), coverage=1.0, duration=None, factor=(-10, 10), name='Pitch_Aug', verbose=0, stateless=True) 
augmented_data = aug_3.augment(Xtrain_2)
'''

'''
# pitch (duration-provided)
aug_3_2 = naa.pitch.PitchAug(re_sampleRate, zone=(0.2, 0.8), coverage=1.0, duration=None, factor=(-10, 10), name='Pitch_Aug', verbose=0, stateless=True) # 찍어보고 duration과 coverage와의 관계 이해
augmented_data = aug_3.augment(Xtrain_2)
'''

"""### mask"""

'''
# mask
aug_4 = naa.mask.MaskAug(sampling_rate=re_sampleRate, zone=(0.2, 0.8), coverage=1.0, duration=None, mask_with_noise=True, name='Mask_Aug', verbose=0, stateless=True) 
augmented_data = aug_4_2.augment(Xtrain_2)
'''

'''
# mask (noise False)
aug_4_2 = naa.mask.MaskAug(sampling_rate=re_sampleRate, zone=(0.2, 0.8), coverage=1.0, duration=None, mask_with_noise=True, name='Mask_Aug', verbose=0, stateless=True) # mask with noise Ture/False
augmented_data = aug_4_3.augment(Xtrain_2)
'''

'''
# mask normalization?
aug = naa.NormalizeAug(method='standard', zone=(0.2, 0.8), coverage=0.3, name='Normalize_Aug', verbose=0, stateless=True) # standard normalization
augmented_data = aug.augment(data)
'''

'''
# weighted random sampler to sample mini-batches uniformly from each class 
# 형태님께서 말씀해주셨던 논문?

# Randomly weighted CNNs for (music) audio classification 
# Randomly weighted CNNs for (music) audio classification github
'''

'''
#찍어보자!

librosa_display.waveplot(df, sr=re_sampleRate, alpha=0.5)
librosa_display.waveplot(augmented_data, sr=re_sampleRate, color='r', alpha=0.25)

plt.tight_layout()
plt.show()

'''

"""## Numpy, Librosa"""

# Changing Speed
# def manipulate(data, speed_factor):
#     return librosa.effects.time_stretch(data, speed_factor)

"""## CV 기법"""

# audio = tfio.audio.AudioIOTensor('gs://cloud-samples-tests/speech/brooklyn.flac')

# print(audio)

'''
# masking
!pip install tensorflow-io[tensorflow] # 이 버전에 맞는 텐서플로-io 설치
import tensorflow as tf 
import tensorflow_io as tfio
audio = tfio.audio.AudioIOTensor(data_preprocessed, dtype=None)

print(audio)
'''

# mixup


# blur

"""##5. Feature Extraction

- Mel spectrogram
"""

def getFeatures(path):
    soundArr,sr=lb.load(path)
    mSpec=lb.feature.melspectrogram(y=soundArr,sr=sr) #sr=16000
    return mSpec

"""**default 값**

sr=22050, S=None, n_fft=2048, hop_length=512, win_length=None, window='hann', center=True, pad_mode='constant', power=2.0,
"""

root_path= root + 'processed_audio_files_7sec_22050/'
mSpec_v=[]
for idx,row in Xval.iterrows():
    path=root_path + row['filename']
    c=getFeatures(path)
    mSpec_v.append(c)

mSpec_val=np.array(mSpec_v)

mSpec_val.shape

root_path= root + 'processed_audio_files_7sec_22050/'
mSpec_t=[]
for idx,row in Xtrain.iterrows():
    path=root_path + row['filename']
    c=getFeatures(path)
    mSpec_t.append(c)

mSpec_train=np.array(mSpec_t)

np.save(root + 'Mel_spectrogram_train_7sec_augmented_data_speed_variation_2.npy',mSpec_train)
np.save(root + 'Mel_spectrogram_val_7sec_augmented_data_speed_variation_2.npy',mSpec_val)

mSpec_train = np.load(root + 'Mel_spectrogram_train_7sec_augmented_data_speed_variation_2.npy')
mSpec_val = np.load(root + 'Mel_spectrogram_val_7sec_augmented_data_speed_variation_2.npy')

len(mSpec_train)

len(mSpec_val)

sr=16000
randFiles = [10 * x for x in range(1,5)]

for i,audioFile in enumerate(randFiles):
  
  plt.figure(figsize=(10, 4))
  plt.title('Mel-Spectrogram') 
  librosa.display.specshow(
      librosa.power_to_db(mSpec_train[audioFile], ref=np.max), y_axis='mel', sr=sr, hop_length=512, x_axis='time')
  plt.colorbar(format='%+2.0f dB')
  
  plt.tight_layout()
  plt.savefig('mSec_nlpaug_speed_variation_2_disease.png')
  plt.show()

"""##6. Build model

- Depthwise Convolution
- ResNet
- Efficient Net

disese model
"""

mSpec_input=keras.layers.Input(shape=(128,302,1),name="mSpecInput")

x = keras.layers.Conv2D(
                filters=32,
                kernel_size=5,
                strides=(2,3),
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(mSpec_input)

x=keras.layers.MaxPooling2D(pool_size=2,padding='valid')(x)

x = keras.layers.Conv2D(
                filters=64,
                kernel_size=3,
                strides=(1,2),
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(x)

x=keras.layers.MaxPooling2D(pool_size=2,padding='valid')(x)

x = keras.layers.Conv2D(
                filters=96,
                kernel_size=2,
                strides=(2,3),
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(x)

x=keras.layers.MaxPooling2D(pool_size=2,padding='valid')(x)

x = keras.layers.Conv2D(
                filters=128,
                kernel_size=2,
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(x)

x=keras.layers.GlobalMaxPooling2D()(x)

x=keras.layers.Dropout(0.2)(x)
x=keras.layers.Dense(50,activation='relu')(x)
x=keras.layers.Dropout(0.3)(x)
x=keras.layers.Dense(25,activation='relu')(x)
x=keras.layers.Dropout(0.3)(x)
output=keras.layers.Dense(8,activation='softmax')(x)

mSpec_model=keras.Model(mSpec_input, output, name="mSpecModel")

mSpec_model.summary()

"""crack & wheeze model"""

mSpec_input=keras.layers.Input(shape=(128,302,1),name="mSpecInput")

x = keras.layers.Conv2D(
                filters=32,
                kernel_size=5,
                strides=(2,3),
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(mSpec_input)

x=keras.layers.MaxPooling2D(pool_size=2,padding='valid')(x)

x = keras.layers.Conv2D(
                filters=64,
                kernel_size=3,
                strides=(1,2),
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(x)

x=keras.layers.MaxPooling2D(pool_size=2,padding='valid')(x)

x = keras.layers.Conv2D(
                filters=96,
                kernel_size=2,
                strides=(2,3),
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(x)

x=keras.layers.MaxPooling2D(pool_size=2,padding='valid')(x)

x = keras.layers.Conv2D(
                filters=128,
                kernel_size=2,
                activation='relu',
                kernel_initializer='he_normal',
                padding='same'
            )(x)

x=keras.layers.GlobalMaxPooling2D()(x)

x=keras.layers.Dropout(0.2)(x)
x=keras.layers.Dense(50,activation='relu')(x)
x=keras.layers.Dropout(0.3)(x)
x=keras.layers.Dense(25,activation='relu')(x)
x=keras.layers.Dropout(0.3)(x)
output=keras.layers.Dense(4,activation='softmax')(x) #class 변화 주의

mSpec_model_cw=keras.Model(mSpec_input, output, name="mSpecModel_cw")

mSpec_model_cw.summary()

"""###training(disease)"""

accuracy='sparse_categorical_accuracy'
sparseLoss=keras.losses.SparseCategoricalCrossentropy()

from keras import backend as K
K.clear_session()
mSpec_model.compile(optimizer='nadam', loss=sparseLoss, metrics=[accuracy])
K.set_value(mSpec_model.optimizer.learning_rate, 0.001)

file_name = '/content/drive/MyDrive/aiffel/aiffelthon/model/checkpoint-only-zero-7sec-001.h5'
my_callbacks = [
    tf.keras.callbacks.EarlyStopping(patience=10),
    tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.1,
                              patience=3, min_lr=1e-12,mode='min'), #미분하다 막히면 lr 변경해줌
    tf.keras.callbacks.ModelCheckpoint(file_name, monitor='val_loss', verbose=0, save_best_only=True,)
]

len(mSpec_train)

len(ytrain)

len(mSpec_val)

len(yval)

ytrain

history=mSpec_model.fit(
    mSpec_train, # fit 할 때 ndarray > tensor로 바꾸는 느낌?
    ytrain,
    validation_data=(mSpec_val,yval),
    epochs=100,verbose=1,
    callbacks=my_callbacks
)

y_pred = mSpec_model.predict(mSpec_val)

"""###training(crackle & wheeze)"""

accuracy='sparse_categorical_accuracy'
sparseLoss=keras.losses.SparseCategoricalCrossentropy()

from keras import backend as K
K.clear_session()
mSpec_model_cw.compile(optimizer='nadam', loss=sparseLoss, metrics=[accuracy])
K.set_value(mSpec_model_cw.optimizer.learning_rate, 0.001)

file_name = '/content/drive/MyDrive/aiffel/aiffelthon/model/checkpoint-only-zero-7sec-cw-001.h5'
my_callbacks_1 = [
    tf.keras.callbacks.EarlyStopping(patience=10),
    tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.1,
                              patience=3, min_lr=1e-12,mode='min'), #미분하다 막히면 lr 변경해줌
    tf.keras.callbacks.ModelCheckpoint(file_name, monitor='val_loss', verbose=0, save_best_only=True,)
]

len(mSpec_val)

len(yval_1)

history=mSpec_model_cw.fit(
    mSpec_train, # fit 할 때 ndarray > tensor로 바꾸는 느낌?
    ytrain_1,
    validation_data=(mSpec_val,yval_1),
    epochs=100,verbose=1,
    callbacks=my_callbacks_1
)

y_pred_1 = mSpec_model_cw.predict(mSpec_val)

"""##7. Evaluate
disease
"""

from sklearn.metrics import confusion_matrix, plot_confusion_matrix
confusion_matrix(np.argmax(y_pred, axis = 1), yval)

from sklearn.metrics import classification_report

target_names=['URTI', 'Healthy', 'Asthma', 'COPD', 'LRTI', 'Bronchiectasis', 'Pheumonia', 'Bronchiolitis']

with open( root+ "clf_report_zero_7sec.txt", "w") as text_file:
    print(classification_report(yval, np.argmax(y_pred, axis = 1), target_names=target_names), file=text_file)

print(classification_report(yval, np.argmax(y_pred, axis = 1), target_names=target_names))

"""crackle & wheeze"""

confusion_matrix(np.argmax(y_pred_1, axis = 1), yval_1)

'''
import seaborn as sns
import matplotlib.pyplot as plt

ax = sns.heatmap(cf_matrix, annot=True, cmap='Blues')

ax.set_title('Seaborn Confusion Matrix with labels\n\n');
ax.set_xlabel('\nPredicted Flower Category')
ax.set_ylabel('Actual Flower Category ');

## Ticket labels - List must be in alphabetical order
ax.xaxis.set_ticklabels(['Setosa','Versicolor', 'Virginia'])
ax.yaxis.set_ticklabels(['Setosa','Versicolor', 'Virginia'])

## Display the visualization of the Confusion Matrix.
plt.show()
'''

target_names=['Normal', 'crackle', 'wheeze', 'both']

with open( root+ "clf_report_zero_7sec_cw.txt", "w") as text_file:
    print(classification_report(yval_1, np.argmax(y_pred_1, axis = 1), target_names=target_names), file=text_file)

print(classification_report(yval_1, np.argmax(y_pred_1, axis = 1), target_names=target_names))

