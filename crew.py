from crewai import Crew,Process
from tasks import research_task,write_task
from agents import article_researcher,article_writer

## Forming the tech focused crew with some enhanced configuration
crew=Crew(
    agents=[article_researcher,article_writer],
    tasks=[research_task,write_task],
    process=Process.sequential,

)

## starting the task execution process wiht enhanced feedback

result=crew.kickoff(inputs={'topic':'tell me about food'})
print(result)