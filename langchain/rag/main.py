from langchain.models import model
from langchain.rag.chain import format_documents, rag_prompt
from langchain.rag.retrievers import retriever

question =  "Where are you located?"
documents = retriever.invoke(
   question
)

context = format_documents(documents)
print(f"~~~~~~CONTEXT~~~~~~~{context}~~~~~~~~~~~~~")

response = (rag_prompt | model).invoke(
    {
    "context": context,
    "question": question
    }
)

print(f"~~~~~~~~~~~~~~~{response}~~~~~~~~~~~~~")