import tensorflow as tf
import tensorflow_probability as tfp
import numpy as np
from advi.model import ADVIModel
from advi.core import run_advi, get_ll_from_advi
from models.ard import Ard
import os
# TODO:
# Nuts trace function is not sufficient.
# Nuts does not have step so not sure what to plot on x axis
# would be good to plot time on x axis like the paper but not sure how
# to do this

# to see tensorboard results type the following in to terminal
# tensorboard --logdir /tmp/summary_chain --port 6006
# and visualise it on your web browser at http://localhost:6006/
# the data will be stored in /tmp/summary_chain

def state_to_log_like(states, data, model):
    sample_mean = tf.reduce_mean(states, axis=[0])
    return model.log_likelihood(data, states)

def state_to_loss(states, data, model):
    sample_mean = tf.reduce_mean(states, axis=[0])
    w, _, _ = sep_params(states, num_features)
    return model.loss(data, w)

summary_writer = tf.summary.create_file_writer('/tmp/summary_chain', flush_millis=10000)
bij = tfp.bijectors.Log()
# Defining summary writer
def run_train(model, train_type, step_size, train_data,
              test_data, num_results=int(100),
              num_burnin_steps=int(100), bijector=bij, m=1):

    # trace_functions for hmc and nuts
    # this function operates at every step of the chain
    # it writes to summary the log likelihood (log pred)
    def trace_fn(state, results):
        with tf.summary.record_if(tf.equal(results.step % 10, 0)):
        tf.summary.scalar("log pred hmc",
                          state_to_log_like(state, test_data, model),
                          step=tf.cast(results.step, tf.int64))
        return ()

      step_is = 0
    def trace_fn_nuts(state, results):
        # trace function for nuts doesnt work yet
        global step_is
        step_is +=1
        tf.summary.scalar("log pred nuts",
                          state_to_log_like(state, test_data, model),
                          step=step_is)
        return ()


    joint_log_prob2 = lambda *args: model.joint_log_prob(train_data, *args)
    # unpack the joint_log_prob2
    
    initial_chain_state = model.return_initial_state()
    # Need to have a starting state for HMC and Nuts for chain

    # Defining kernels for HMC and NUTS
    adaptive_hmc = tfp.mcmc.SimpleStepSizeAdaptation(
        tfp.mcmc.HamiltonianMonteCarlo(
          target_log_prob_fn=joint_log_prob2,
          num_leapfrog_steps=3,
          step_size=step_size),
      num_adaptation_steps=int(num_burnin_steps * 0.8))

    nuts = tfp.mcmc.NoUTurnSampler(
        target_log_prob_fn=joint_log_prob2,
        step_size=step_size,
        max_tree_depth=10,
        max_energy_diff=1000.0,
        unrolled_leapfrog_steps=1, parallel_iterations=10, seed=None, name=None)

    # Ru HMC / NUTS / ADVI
    @tf.function # tf.function creates a graph of following function.
    def run_chain_hmc():
        print("running hmc chain")
      # Run the chain (with burn-in).
        states, is_accepted = tfp.mcmc.sample_chain(
            num_results=num_results,
            num_burnin_steps=num_burnin_steps,
            current_state=initial_chain_state,
            kernel=adaptive_hmc,
            trace_fn=trace_fn)
        return states, is_accepted

    @tf.function
    def run_chain_nuts():
        print("running nuts chain")
        # Run the chain (with burn-in).
        states, is_accepted = tfp.mcmc.sample_chain(
            num_results= num_results,
            num_burnin_steps=num_burnin_steps,
            current_state=initial_chain_state,
            kernel=nuts,
            trace_fn=trace_fn_nuts)
        return states, is_accepted
    
    if(train_type == "advi"):
        bij = tfp.bijectors.Log()
        num_results = num_results
        step_size = step_size
        # run the advi
        with summary_writer.as_default():
            theta = run_advi(model.num_params,
                             joint_log_prob2,
                             model.log_likelihood,
                             test_data,
                             bijector=bijector, m=m)
            summary_writer.close()
    if (train_type == "hmc"):
        with summary_writer.as_default():
            states, is_accepted = run_chain_hmc()
            summary_writer.close()
      
    if (train_type == "nuts"):
        with summary_writer.as_default():
              theta = run_chain_nuts()
        summary_writer.close()



