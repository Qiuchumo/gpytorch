import torch
import gpytorch
from gpytorch.lazy import LazyVariable
from .posterior_strategy import PosteriorStrategy


class DefaultPosteriorStrategy(PosteriorStrategy):
    def alpha_size(self):
        return self.var.size()[1]

    def exact_posterior_alpha(self, train_mean, train_y):
        res = gpytorch.inv_matmul(self.var, train_y - train_mean)
        return res

    def exact_posterior_mean(self, test_mean, alpha):
        from gpytorch.lazy import MulLazyVariable
        if isinstance(self.var, MulLazyVariable):
            result = self.var.cpu().matmul(alpha.cpu()) + test_mean.cpu()
            print 'Got it!'
            return result
        elif isinstance(self.var, LazyVariable):
            return self.var.matmul(alpha) + test_mean
        return torch.addmv(test_mean, self.var, alpha)

    def exact_posterior_covar(self, test_train_covar, train_test_covar, test_test_covar):
        # TODO: Add a diagonal only mode / use implicit math
        if isinstance(train_test_covar, LazyVariable):
            train_test_covar = train_test_covar.evaluate()
        if isinstance(test_train_covar, LazyVariable):
            test_train_covar = train_test_covar.t()
        if isinstance(self.var, LazyVariable):
            test_test_covar = test_test_covar.evaluate()

        test_test_covar_correction = torch.mm(test_train_covar, gpytorch.inv_matmul(self.var, train_test_covar))
        return test_test_covar.sub(test_test_covar_correction)

    def variational_posterior_alpha(self, variational_mean):
        return gpytorch.inv_matmul(self.var, variational_mean)

    def variational_posterior_mean(self, alpha):
        return self.var.matmul(alpha)

    def variational_posterior_covar(self, induc_test_covar, chol_variational_covar,
                                    test_test_covar, induc_induc_covar):
        # left_factor = K_{mn}K_{nn}^{-1}(S - K_{nn})
        variational_covar = chol_variational_covar.t().matmul(chol_variational_covar)
        left_factor = torch.mm(self.var, gpytorch.inv_matmul(induc_induc_covar,
                                                             variational_covar - induc_induc_covar))
        # right_factor = K_{nn}^{-1}K_{nm}
        right_factor = gpytorch.inv_matmul(induc_induc_covar, induc_test_covar)
        # test_test_covar = K_{mm} + K_{mn}K_{nn}^{-1}(S - K_{nn})K_{nn}^{-1}K_{nm}
        return test_test_covar + left_factor.mm(right_factor)
