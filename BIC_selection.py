######################################################################
# BIC_selection.py
# Implements a grid-search based selection of the hyperparameters
# that minimize BIC of model.
######################################################################

# %% import statements
import numpy as np
import subprocess

# %% directories
ACTIVE_LEARNING_DIR = "active_learning_sims"

GENERAL_PREFIX = "/mnt/c/Users/apare/Desktop/KimResearchGroup/Spring2022/"
TO_CITRUSS = GENERAL_PREFIX + "mlcggm/Mega-sCGGM/citruss.py"
TO_DATA = "input_simulation/simulateCodeTemp/"


# %% main function
def main():
    print("BIC Hyperparameter Selection")

    fXm = GENERAL_PREFIX + TO_DATA + "missing35/Xm1.txt"
    fXp = GENERAL_PREFIX + TO_DATA + "missing35/Xp1.txt"
    fYm = GENERAL_PREFIX + TO_DATA + "missing35/Ym1.txt"
    fYp = GENERAL_PREFIX + TO_DATA + "missing35/Yp1.txt"
    fYsum = GENERAL_PREFIX + TO_DATA + "missing35/Ysum1.txt"

    Xm = np.loadtxt(fXm)
    Xp = np.loadtxt(fXp)
    Xs = Xm + Xp

    Ym = np.loadtxt(fYm)
    Yp = np.loadtxt(fYp)
    Ysum = np.loadtxt(fYsum)

    # F = np.loadtxt("missing35/1F.txt")
    # V = np.loadtxt("missing35/1V.txt")
    # Gamma = np.loadtxt("missing35/1Gamma.txt")
    # Psi = np.loadtxt("missing35/1Psi.txt")

    regV = np.arange(0, 0.86, 0.05)
    regF = np.arange(0, 0.86, 0.05)
    regGamma = np.arange(0, 0.86, 0.05)
    regPsi = np.arange(0, 0.86, 0.05)

    output_prefix = GENERAL_PREFIX + TO_DATA + "BIC_selection/"
    N, q = Xm.shape
    _, p = Ym.shape

    bic_result = [None for _ in range(len(regV))]
    llik_results = [None for _ in range(len(regV))]
    for i in range(len(regV)):
        bic_result[i] = get_BIC(fXm, fXp, fYm, fYp, fYsum, regV[i], regF[i], regGamma[i], regPsi[i],
                                Xm, Xp, Ym, Yp, Ysum, output_prefix, N, q, p)

    print(bic_result)

# %% BIC grid search


def get_BIC(fXm, fXp, fYm, fYp, fYsum, regV, regF, regGamma, regPsi,
            Xm, Xp, Ym, Yp, Ysum,
            output_prefix, N, q, p, citruss_path=TO_CITRUSS):
    """
    Estimate the parameters of a model given the input data and 
    hyperparameters. Compute the BIC. 

    Note: must give full name of file path. 
    """
    # first, run citruss
    run_citruss(fYsum, fYm, fYp, fXm, fXp, output_prefix,
                regV, regF, regGamma, regPsi, N, q, p, citruss_path)

    # now, load the output data
    Fmat = np.loadtxt(output_prefix + "F.txt")
    Vmat = np.loadtxt(output_prefix + "V.txt")
    GammaMat = np.loadtxt(output_prefix + "Gamma.txt")
    PsiMat = np.loadtxt(output_prefix + "Psi.txt")

    # return the resulting BIC and log-likelihood
    return (BIC(Xm, Xp, Ym, Yp, Ysum, Fmat, Vmat, GammaMat, PsiMat,
                regF, regV, regGamma, regPsi),
            llik(Xm, Xp, Ym, Yp, Ysum, Fmat, Vmat, GammaMat, PsiMat,
                 regF, regV, regGamma, regPsi))


# %% Bayesian Information Criterion
def BIC(Xm, Xp, Ym, Yp, Ysum, Fmat, Vmat, GammaMat, PsiMat, regF,
        regV, regGamma, regPsi):
    """
    Returns the Bayesian Information Criterion of the estimated 
    CGGM given the parameters used to estimate the model and the 
    final estimate. 
    """
    nnzF = nnz(Fmat)
    nnzV = nnz(Vmat)
    nnzGamma = nnz(GammaMat)
    nnzPsi = nnz(PsiMat)
    k = nnzF + nnzV + nnzGamma + nnzPsi
    n = Xm.shape[0]

    llik_val = llik(Xm, Xp, Ym, Yp, Ysum, Fmat, Vmat, GammaMat, PsiMat,
                    regF, regV, regGamma, regPsi)

    return (k * np.log(n) + 2 * llik_val, k)


# %% log-likelihood
def llik(Xm, Xp, Ym, Yp, Ysum, Fmat, Vmat, GammaMat, PsiMat, regF,
         regV, regGamma, regPsi):
    """
    Returns the NEGATIVE log-likelihood of the model given its parameters.
    """
    # get Xs, Xd
    Xs = Xm + Xp
    Xd = Xm - Xp

    # get Ys, Yd
    Ys = Ysum
    Yd = Ym - Yp

    def get_prob(i):
        return individual_prob(Xs, Xd, Ys, Yd, Fmat, Vmat, GammaMat, PsiMat, i, log=True)

    llik_arr = np.array([get_prob(i) for i in range(Xs.shape[0])])

    return -np.sum(llik_arr) + \
        regF * np.sum(np.abs(Fmat)) + \
        regV * np.sum(np.abs(Vmat)) + \
        regGamma * np.sum(np.abs(GammaMat)) + \
        regPsi * np.sum(np.abs(PsiMat))


# calculate the probability for each individual
def individual_prob(Xs, Xd, Ys, Yd, Fmat, Vmat, GammaMat, PsiMat, i, log=False):
    """
    Calculates the probability of the data given the parameters for a single 
    individual i. 
    """
    ifin = np.isfinite(Yd[i])
    yd = Yd[i, ifin]

    if log:
        return prob_sum_individual(Ys[i], Xs[i], Vmat, Fmat, log=True) + \
            prob_diff_individual(yd, Xd[i], np.diag(
                GammaMat[ifin, ifin]), PsiMat[:, ifin], log=True)
    else:
        return prob_sum_individual(Ys[i], Xs[i], Vmat, Fmat) * \
            prob_diff_individual(yd, Xd[i], np.diag(
                GammaMat[ifin, ifin]), PsiMat[:, ifin])


def prob_diff_individual(Yd, Xd, Gamma, Psi, log=False):
    """
    Calculates equation (4b) from manuscript ASE_net.
    """
    # number of genes
    q, _ = Gamma.shape

    gamma_inv = 1 / np.diag(Gamma)
    if log:
        c1 = (q/2) * np.log(2 * np.pi)
        c2 = -0.5 * np.sum(np.log(np.diag(Gamma)))
        c3 = (-0.5 * (Xd.T @ Psi @ np.diag(gamma_inv) @ Psi.T @ Xd))
        num = -0.5 * (Yd.T @ Gamma @ Yd - Xd.T @ Psi @ Yd)
        denom = c1 + c2 + c3
        return num - denom
    else:
        # normalization constant
        c1 = np.power(2 * np.pi, q/2)
        c2 = np.power(np.prod(np.diag(Gamma)), -0.5)
        c3 = np.exp(-0.5 * (Xd.T @ Psi @ np.diag(gamma_inv) @ Psi.T @ Xd))
        Z = c1 * c2 * c3
        return np.exp(-0.5 * (Yd.T @ Gamma @ Yd - Xd.T @ Psi @ Yd)) / Z


def prob_sum_individual(Ys, Xs, V, F, log=False):
    """
    Calculates equation (4a) from manuscript ASE_net.
    """
    # number of genes
    q, _ = V.shape

    if log:
        c1 = (q / 2) * np.log(2 * np.pi)
        c2 = -0.5 * np.log(np.linalg.det(V))
        c3 = -0.5 * (Xs.T @ F @ np.linalg.inv(V) @ F.T @ Xs)
        num = -0.5 * (Ys.T @ V @ Ys - Xs.T @ F @ Ys)
        denom = c1 + c2 + c3
        return num - denom
    else:
        # normalization constant
        c1 = np.power(2 * np.pi, q / 2)
        c2 = np.power(np.linalg.det(V), -0.5)
        c3 = np.exp(-0.5 * (Xs.T @ F @ np.linalg.inv(V) @ F.T @ Xs))
        Z = c1 * c2 * c3
        return np.exp(-0.5 * (Ys.T @ V @ Ys - Xs.T @ F @ Ys)) / Z


# %% grid search
def hyper_grid(minF, maxF, minV, maxV, minGamma, maxGamma, minPsi, maxPsi,
               resolution=[10, 10, 10, 10]):
    """
    Returns a grid of hyperparameter values to be used for a search.
    """
    valF = np.linspace(minF, maxF, resolution[0])
    valV = np.linspace(minV, maxV, resolution[1])
    valDelta = np.linspace(minGamma, maxGamma, resolution[2])
    valPi = np.linspace(minPsi, maxPsi, resolution[3])

    grid = np.meshgrid(valF, valV, valDelta, valPi, indexing='ij')
    return grid


def nnz(matrix):
    """
    Gets the number of non-zero entries in a matrix.
    """
    return len(np.nonzero(matrix)[0])


# %% for running citruss.py
def run_citruss(fysum, fym, fyp, fxm, fxp, output_prefix,
                vreg, freg, gammareg, psireg, N, q, p,
                citruss_path):
    """
    Run citruss on a dataset with the given parameters.
    """
    cmd_list = ['python', citruss_path, str(N), str(q), str(p),
                fysum, fym, fyp, fxm, fxp, output_prefix,
                str(vreg), str(freg), str(gammareg), str(psireg)]

    subprocess.run(cmd_list, check=True)


# %% execute main

if __name__ == '__main__':
    main()

# %%
