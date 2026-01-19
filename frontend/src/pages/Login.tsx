import { useState } from "react";
import api from "../api/axios";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import axios from "axios";


const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const navigate = useNavigate();
const { refetchAuth } = useAuth();

const handleLogin = async () => {
  setError("");

  try {
    const response = await api.post("/auth/login", {
      username,
      password,
    });

    if (response.status === 200) {
      await refetchAuth();
      navigate("/dashboard");
      return;
    }

    // Safety fallback
    setError("Invalid credentials");
  } catch (err: unknown) {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      setError("Invalid credentials");
    }
  }
};



  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-96 p-6 border rounded">
        <h1 className="text-xl font-bold mb-4">Login</h1>

        {error && <p className="text-red-500">{error}</p>}

        <input
          className="w-full border p-2 mb-3"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          type="password"
          className="w-full border p-2 mb-3"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          type="button"
          onClick={handleLogin}
          className="w-full bg-black text-white p-2"
        >
          Login
        </button>
      </div>
    </div>
  );
};

export default Login;
