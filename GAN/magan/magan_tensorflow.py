import tensorflow as tf
#from tensorflow.examples.tutorials.mnist import input_data
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
import random


mb_size = 1
X_dim = 109568
z_dim = 64
h_dim = 128
dlr = 1e-10
glr = 1e-4
lr = 5e-5
n_iter = 1000
n_epoch = 1000
N = n_iter * mb_size  # N data per epoch

#mnist = input_data.read_data_sets('../../MNIST_data', one_hot=True)
mnist = np.load("test0.npy")
mnist = list(mnist)
newMnist = []
for n in mnist:
    if n.shape == (856, 1025):
        n = n[:, :128]
        newMnist.append(n.flatten())
mnist = newMnist
newMnist = []
print(len(mnist))

def plot(samples):
    fig = plt.figure(figsize=(1, 1))
    gs = gridspec.GridSpec(1, 1)
    gs.update(wspace=0.05, hspace=0.05)

    for i, sample in enumerate(samples):
        ax = plt.subplot(gs[i])
        plt.axis('off')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_aspect('equal')
        plt.imshow(sample.reshape(856, 128), cmap='Greys_r')

    return fig


def xavier_init(size):
    in_dim = size[0]
    xavier_stddev = 1. / tf.sqrt(in_dim / 2.)
    return tf.random_normal(shape=size, stddev=xavier_stddev)


X = tf.placeholder(tf.float32, shape=[None, X_dim])
z = tf.placeholder(tf.float32, shape=[None, z_dim])
m = tf.placeholder(tf.float32)

D_W1 = tf.Variable(xavier_init([X_dim, h_dim]))
D_b1 = tf.Variable(tf.zeros(shape=[h_dim]))
D_W2 = tf.Variable(xavier_init([h_dim, X_dim]))
D_b2 = tf.Variable(tf.zeros(shape=[X_dim]))

G_W1 = tf.Variable(xavier_init([z_dim, h_dim]))
G_b1 = tf.Variable(tf.zeros(shape=[h_dim]))
G_W2 = tf.Variable(xavier_init([h_dim, X_dim]))
G_b2 = tf.Variable(tf.zeros(shape=[X_dim]))

theta_G = [G_W1, G_W2, G_b1, G_b2]
theta_D = [D_W1, D_W2, D_b1, D_b2]


def sample_z(m, n):
    return np.random.uniform(-1., 1., size=[m, n])


def G(z):
    G_h1 = tf.nn.relu(tf.matmul(z, G_W1) + G_b1)
    G_log_prob = tf.matmul(G_h1, G_W2) + G_b2
    G_prob = tf.nn.sigmoid(G_log_prob)
    return G_prob


def D(X):
    D_h1 = tf.nn.relu(tf.matmul(X, D_W1) + D_b1)
    X_recon = tf.matmul(D_h1, D_W2) + D_b2
    return tf.reduce_sum((X - X_recon)**2, 1)


G_sample = G(z)

D_real = D(X)
D_fake = D(G_sample)

D_recon_loss = tf.reduce_mean(D_real)
D_loss = tf.reduce_mean(D_real + tf.maximum(0., m - D_fake))
G_loss = tf.reduce_mean(D_fake)

D_recon_solver = (tf.train.AdamOptimizer(learning_rate=lr)
                  .minimize(D_recon_loss, var_list=theta_D))
D_solver = (tf.train.AdamOptimizer(learning_rate=lr)
            .minimize(D_loss, var_list=theta_D))
G_solver = (tf.train.AdamOptimizer(learning_rate=lr)
            .minimize(G_loss, var_list=theta_G))

sess = tf.Session()
sess.run(tf.global_variables_initializer())

if not os.path.exists('out/'):
    os.makedirs('out/')


# Pretrain
for it in range(2*n_iter):
    #X_mb, _ = mnist.train.next_batch(mb_size)
    X_mb = np.array([random.sample(mnist, 1)[0]])

    _, D_recon_loss_curr = sess.run(
        [D_recon_solver, D_recon_loss], feed_dict={X: X_mb}
    )

    if it % 1000 == 0:
        print('Iter-{}; Pretrained D loss: {:.4}'.format(it, D_recon_loss_curr))


i = 0
# Initial margin, expected energy of real data
margin = sess.run(D_recon_loss, feed_dict={X: mnist})
s_z_before = np.inf

# GAN training
for t in range(n_epoch):
    s_x, s_z = 0., 0.

    for it in range(n_iter):
        #X_mb, _ = mnist.train.next_batch(mb_size)
        X_mb = np.array([random.sample(mnist, 1)[0]])
        while X_mb.shape != (1, 109568):
            print(X_mb.shape)
            X_mb = np.array([random.sample(mnist, 1)[0]])
        z_mb = sample_z(mb_size, z_dim)

        _, D_loss_curr, D_real_curr = sess.run(
            [D_solver, D_loss, D_real], feed_dict={X: X_mb, z: z_mb, m: margin}
        )

        # Update real samples statistics
        s_x += np.sum(D_real_curr)

        _, G_loss_curr, D_fake_curr = sess.run(
            [G_solver, G_loss, D_fake],
            feed_dict={X: X_mb, z: sample_z(mb_size, z_dim), m: margin}
        )

        # Update fake samples statistics
        s_z += np.sum(D_fake_curr)

    # Update margin
    if (s_x / N < margin) and (s_x < s_z) and (s_z_before < s_z):
        margin = s_x / N

    s_z_before = s_z

    # Convergence measure
    Ex = s_x / N
    Ez = s_z / N
    L = Ex + np.abs(Ex - Ez)

    # Visualize
    print('Epoch: {}; m: {:.4}, L: {:.4}'.format(t, margin, L))

    samples = sess.run(G_sample, feed_dict={z: sample_z(1, z_dim)})

    print(samples)
    np.save('out/{}'.format(str(i).zfill(3)), samples.reshape(856,128))

    fig = plot(samples)
    plt.savefig('out/{}.png'
                .format(str(i).zfill(3)), bbox_inches='tight', dpi=1000)
    plt.close(fig)
    # fig = plot(X_mb)
    # plt.savefig('out/{}test.png'
    #             .format(str(i).zfill(3)), bbox_inches='tight', dpi=1000)
    # plt.close(fig)
    i += 1
