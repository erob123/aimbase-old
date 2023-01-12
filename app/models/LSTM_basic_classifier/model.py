from threading import Lock
import tensorflow as tf
from tensorflow.keras import layers
import math
import pandas as pd

# load the dataset
chat816 = pd.read_csv(
    './data/(EROB) MM_Dataset_816_CSVsanitized_flights.csv')

# Make a text-only dataset (without labels), then call adapt
train_text = tf.constant(chat816['Column12'].astype(str).values)

# number of unique words in the dataset after punctuation filtering
word_count_layer = layers.TextVectorization()
word_count_layer.adapt(train_text)
num_words = len(word_count_layer.get_vocabulary())
print(f'There are {num_words} unique words in this dataset')

# tokenizer
# https://www.analyticsvidhya.com/blog/2020/05/what-is-tokenization-nlp/
# https://www.tensorflow.org/api_docs/python/tf/keras/layers/TextVectorization
# https://www.tensorflow.org/tutorials/keras/text_classification
max_features = math.floor(num_words * .25)
sequence_length = 25

vectorize_layer = layers.TextVectorization(
    max_tokens=max_features,
    output_mode='int',
    ngrams=3,
    output_sequence_length=sequence_length)

# build vocab for this dataset
vectorize_layer.adapt(train_text)

# save the vocabulary as a standard python list
vocab = vectorize_layer.get_vocabulary()

# how far did ngram truly go
max_ngram_size = 0
for item in vocab:
    max_ngram_size = max(max_ngram_size, len(item.split()))


# define the LSTM
def LSTM(rnn_units, stateful=True):
    return tf.keras.layers.LSTM(
        rnn_units,
        return_sequences=True,
        recurrent_initializer='glorot_uniform',
        recurrent_activation='sigmoid',
        stateful=stateful,
    )

### Defining the RNN Model ###
def build_model(vocab_size, num_class, embedding_dim, rnn_units, batch_size):

    first_layer = tf.keras.layers.Embedding(vocab_size, embedding_dim, mask_zero=True) if batch_size is None else tf.keras.layers.Embedding(
        vocab_size, embedding_dim, batch_input_shape=[batch_size, None], mask_zero=True)

    LSTM_layer = LSTM(rnn_units, stateful=False) if batch_size is None else LSTM(rnn_units)

    model = tf.keras.Sequential([

        # Layer 0: mask zeros in time steps, i.e., data does not exist
        # https://www.tensorflow.org/api_docs/python/tf/keras/layers/Masking
        # https://www.tensorflow.org/guide/keras/masking_and_padding
        # tf.keras.layers.Masking(mask_value=0.0),

        # Layer 1: Embedding layer to transform indices into dense vectors
        #   of a fixed embedding size
        # mask zeros for diff length inputs
        first_layer,

        # dropout to prevent overfitting
        tf.keras.layers.Dropout(.2),

        # Layer 2: LSTM with `rnn_units` number of units.
        LSTM_layer,

        # dropout to prevent overfitting
        tf.keras.layers.Dropout(.2),

        # Layer 3: Dense (fully-connected) layer that transforms the LSTM output
        #   into the vocabulary size. NOTE: output will need to have softmax applied...no activation
        tf.keras.layers.Dense(num_class)
    ])

    return model


#################################################################
### Hyperparameters relevant for inference (make sure they match
# those used in training) ###
# Model parameters:
num_classes = 3
embedding_dim = 8
rnn_units = 128  # Experiment between 1 and 2048

# # Checkpoint location:
checkpoint_dir = './app/models/LSTM_basic_classifier/training_checkpoints'
############## Inference ######################
class Model:
    def __init__(self):

        # batch size None for inference, remove statefulness and allow any size input
        self.model = build_model(vocab_size=len(vocab), num_class=num_classes, embedding_dim=embedding_dim, rnn_units=rnn_units, batch_size=None)

        # Restore the model weights for the last checkpoint after training
        self.model.load_weights(tf.train.latest_checkpoint(checkpoint_dir))
        self.model.build(tf.TensorShape([1, None]))

        # use to manage concurrent requests
        self.lock = Lock()

    ## Prediction of a chat class ###
    def classify(self, chats):
        with self.lock:
            # convert to list if needed
            chats = [chats] if isinstance(chats, str) else chats

            # up the dimension if single inference...its hacky i know...
            single_item = False
            if len(chats) == 1:
                chats.append("")
                single_item = True

            # Evaluation step (generating ABC text using the learned RNN model)
            input_eval = vectorize_layer(tf.squeeze(chats))
            pred = self.model(input_eval, training=False)
            pred = tf.nn.softmax(tf.squeeze(pred)[:, -1, :])
            output_labels = tf.argmax(pred, axis=1)

            return output_labels if not single_item else [output_labels[0]]

    def classify_label(self, chats):
        encoded_labels = self.classify(chats)
        labels = ['recycle', 'review', 'action']
        return list(map(lambda label: labels[label], encoded_labels))

    def classify_single_label(self, chat):
        return self.classify_label([chat])[0]

# use for DI
model = Model()
def get_model():
    return model
