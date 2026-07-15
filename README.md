# Cinematic Compositor

Add-on para Blender que reúne controles de pós-processamento cinematográfico e color grading diretamente na barra lateral do Compositor e da Viewport 3D.

## Recursos

- Bloom, streaks e lens ghosts
- Nitidez, curvas RGB e balanço de cor
- Ajustes de brilho, contraste, matiz e saturação
- Vinheta e granulação cinematográfica
- Integração com o grupo **Tune Image** disponível nos assets essenciais do Blender

## Requisitos

- Blender 3.0 ou mais recente

## Instalação

1. Baixe o arquivo `cinematic_compositor.py`.
2. No Blender, abra **Edit > Preferences > Add-ons**.
3. Use **Install from Disk** e selecione o arquivo baixado.
4. Ative **Custom Cinematic Compositor**.

O painel ficará disponível em **Compositor > Sidebar > Cinematic** e em **3D Viewport > Sidebar > Cinematic**.

## Estrutura do projeto

- `cinematic_compositor.py`: add-on distribuível e instalável.
- `examples/`: arquivos Blender de demonstração e teste manual.
- `tools/diagnostics/`: scripts auxiliares para investigar APIs e nodes do Blender.
- `.github/workflows/`: verificações executadas automaticamente pelo GitHub.

## Desenvolvimento

Para validar a sintaxe sem abrir o Blender:

```powershell
python -m py_compile cinematic_compositor.py
```

Os testes de integração devem ser executados pelo próprio Blender, pois o módulo `bpy` só existe nesse ambiente.

## Status

O projeto está em desenvolvimento. A API de nodes do Blender pode variar entre versões; valide alterações nas versões do Blender que pretende suportar.

