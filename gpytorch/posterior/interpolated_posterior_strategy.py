import gpytorch
from .posterior_strategy import PosteriorStrategy
from torch.autograd import Variable


class InterpolatedPosteriorStrategy(PosteriorStrategy):
    def __init__(self, var, grid, interp_left, interp_right):
        """
        Assumes that var is represented by interp_left * grid * interp_right^T

        Args:
        - var (LazyVariable) - the variable to define the PosteriorStrategy for
        - grid (LazyVariable) - represents the grid matrix
        - interp_left (Sparse Tensor) - the left interpolation matrix of the grid
        - interp_right (Sparse Tensor) - the right interpolation matrix of the grid
        """
        super(InterpolatedPosteriorStrategy, self).__init__(var)
        self.grid = grid
        self.interp_left = interp_left
        self.interp_right = interp_right

    def alpha_size(self):
        return self.grid.size()[1]

    def exact_posterior_alpha(self, train_mean, train_y):
        train_residual = (train_y - train_mean).unsqueeze(1)
        gpytorch.functions.max_cg_iterations *= 10
        alpha = self.var.inv_matmul(train_residual)
        gpytorch.functions.max_cg_iterations /= 10
        alpha = gpytorch.dsmm(Variable(self.interp_right.data.t()), alpha)
        alpha = self.grid.matmul(alpha)
        return alpha.squeeze()

    def exact_posterior_mean(self, test_mean, alpha):
        alpha = alpha.unsqueeze(1)
        return test_mean.add(gpytorch.dsmm(self.interp_left, alpha).squeeze())
