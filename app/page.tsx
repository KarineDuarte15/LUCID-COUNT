// app/page.tsx
'use client'; 

import React, { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter(); 
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault(); 
    console.log('Tentativa de login com:', { email, password });
    router.push('/dashboard'); 
  };

  return (
    <main className="flex items-center justify-center min-h-screen bg-background text-primary-text p-4">
      {/* A MUDANÇA PRINCIPAL ESTÁ AQUI:
        - `max-w-md` limita a largura do formulário em ecrãs grandes.
        - `space-y-8` adiciona um espaçamento vertical generoso entre os elementos filhos.
      */}
      <div className="max-w-md p-8 space-y-8 bg-container rounded-xl shadow-lg border border-gray-900">
        
        <div className="flex justify-center">
          <Image
            src="/logo.png"
            alt="Logo Aci Contabilidade"
            width={600} // O logo agora parecerá mais proporcional
            height={400}
            priority
          />
        </div>

        <h1 className="text-2xl font-bold text-center text-accent">
          Acesso ao Painel
        </h1>

        {/* A classe `space-y-6` adiciona espaço entre os campos do formulário */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label 
              htmlFor="email" 
              className="text-sm font-medium block mb-2"
            >
              Email
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="seu@email.com" // Placeholder adicionado
              required
            />
          </div>

          <div>
            <label 
              htmlFor="password" 
              className="text-sm font-medium block mb-2"
            >
              Senha
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="••••••••" // Placeholder adicionado
              required
            />
          </div>

          <button
            type="submit"
            className="w-full py-2 px-4 bg-accent text-background font-bold rounded-md hover:bg-accent/90 transition-colors duration-300"
          >
            Entrar
          </button>

          <div className="text-center">
            <a href="#" className="text-sm text-secondary-text hover:text-accent transition-colors">
              Esqueceu-se da sua senha?
            </a>
          </div>
        </form>
      </div>
    </main>
  );
}