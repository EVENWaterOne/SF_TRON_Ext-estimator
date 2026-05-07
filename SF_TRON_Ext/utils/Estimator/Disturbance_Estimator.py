import os

import torch


class Disturbance_Estimator(torch.nn.Module):
    def __init__(self, EstimatorParam, device):
        super().__init__()
        self.history_len = EstimatorParam.history_len
        self.obs_dim = EstimatorParam.obs_dim
        self.latent_dim = EstimatorParam.latent_dim
        self.model_path = EstimatorParam.model_path
        self.device = device

        input_dim = self.history_len * self.obs_dim
        layers = []
        prev_dim = input_dim
        for hidden_dim in EstimatorParam.hidden_layers:
            layers.append(torch.nn.Linear(prev_dim, hidden_dim))
            layers.append(torch.nn.ELU())
            prev_dim = hidden_dim
        layers.append(torch.nn.Linear(prev_dim, self.latent_dim))

        self.network = torch.nn.Sequential(*layers).to(self.device)
        self.optimizer = torch.optim.Adam(self.parameters(), lr=EstimatorParam.lr)
        self.loss_fn = torch.nn.MSELoss()

    def forward(self, history):
        history = history.reshape(history.shape[0], -1)
        return self.network(history)

    def predict(self, history):
        return self.forward(history)

    def update(self, history, target_force):
        prediction = self.forward(history)
        loss = self.loss_fn(prediction, target_force)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item(), prediction.detach()

    def save_model(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.state_dict(), self.model_path)

    def load_model(self):
        self.load_state_dict(torch.load(self.model_path))

    def save_checkpoint(self, episode):
        base, ext = os.path.splitext(self.model_path)
        torch.save(self.state_dict(), f"{base}_ckpt{episode}{ext}")
